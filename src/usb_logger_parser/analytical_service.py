"""
analytical_service.py

Detects, quantifies, and classifies temperature spikes from logger data.

Workflow:
1.	Ingest cleaned temperature readings
2.	Use ‘status’ column to categorize temperature readings into ‘too_high’ / ‘too_low’ depending on the temperature limits specified in Limits class
3.	Add cumulative spike_id to temperature readings based on the change between ‘status’ field – when status changes, next cumulative spike id is initiated.
4.	Extract information on total duration of spikes over 24hr period by:
a.	Calculating time difference in minutes between individual temperature readings
b.	Filtering  temperature readings that are in ‘too_high’ and ‘too_low’ categories
c.	Including new field ‘last_spike_of_day’ based on the difference between dates – when date changes, previous reading is the last spike of the day.
d.	Adding 24hr window to the last spike of the day
e.	Filtering last_spike_of_day column by True values
f.	Using original data and information from (e) to sum time difference in minutes from (a) to determine the total duration of all spikes over the 24hr period using last spike of day as a starting point.
5.	Extracts information about temperature excursions (spikes) by:
a.	Grouping temperature readings into ‘too_high’ and ‘too_low’ groups and determining group extremes such as max/min temperature, max/min datetime, max/min date and individual spike group duration in mins
6.	Merge  (4) and (5) to include total spike duration over the period of 24hr into the excursions dataframe.
7.	Renumber spikes to start from 1 and restart spike count on the next day
8.	Check spikes against single and total spike duration limits provided and mark spikes as Fail or Pass.
9.	For spikes in Fail category, calculate Mean Kinetic Temperature over 24hr period using failed spike as a starting point for ± 12hr period calculation
10.	Prepare spike summary to feed into Reporting Service.

"""

import math
from datetime import timedelta

import numpy as np
import pandas as pd

from usb_logger_parser.helper_functions import (
    extract_to_list,
    get_extreme_date_time,
    get_extreme_temp,
    get_spike_duration,
    insert_metadata_header,
)


class AnalyticalService:
    def __init__(self):
        pass

    def analyze_spikes(self, storage_units):
        """returns spike information for each storage unit"""
        spike_dict_list = []
        for unit in storage_units:
            df = unit.temp_data.copy()
            df = self.add_status_column(df, unit.low_alarm, unit.high_alarm)
            df = self.add_cumulat_spike_id(df)
            df_total_spike_duration = self.prepare_df_last_spike_of_day(df)
            df_excursions = self.get_extremes_info(df)
            df = self.prepare_excursions_df(df_total_spike_duration, df_excursions)
            df = self.renumber_spikes(df)
            df = self.check_against_limits(
                df, unit.spike_duration, unit.total_spikes_duration
            )
            df = self.find_mkt(df, unit.temp_data)
            spike_info = self.prepare_spike_summary_for_reporting(df, unit.metadata)
            spike_dict_list.append(spike_info)
        return spike_dict_list

    def add_status_column(self, df, low_alarm, high_alarm):
        """finds spikes and adds 'status' column, which will be used to filter spike max (if 'too_high') or min (if 'too_low') temperature"""
        df.loc[df["celsius"] > high_alarm, "status"] = "too_high"
        df.loc[df["celsius"] < low_alarm, "status"] = "too_low"
        return df

    def add_cumulat_spike_id(self, df):
        """adds cumulative spike id for grouping spike information"""
        df["cumulat_spike_id"] = (df["status"] != df["status"].shift()).cumsum()
        return df

    def add_gap_mins(self, df):
        """groups spike info and finds delta datetime between individual readings within the group,
        which will be used to calculate total_spike_duration"""
        df["reading_gap_mins"] = (
            df.groupby("cumulat_spike_id")["date_time"].diff().dt.total_seconds() / 60
        )
        return df

    def prepare_df_last_spike_of_day(self, df):
        """returns dataframe where: last spike of the day is determined, 24hr window before the last spike is defined
        and total duration of temp spikes is determined."""
        df_original = df
        df_last_spike = self.add_gap_mins(df_original)
        df_last_spike = self.filter_by_status(df_last_spike)
        df_last_spike = self.add_last_spike_check(df_last_spike)
        df_last_spike = self.prepare_24hr_window_start(df_last_spike)
        df_last_spike = self.filter_by_last_spike(df_last_spike)
        df_last_spike = self.determine_spike_duration_24hr_mins(
            df_last_spike, df_original
        )
        return df_last_spike

    def filter_by_status(self, df):
        filtered_df = df[df["status"].isin(["too_high", "too_low"])][
            ["cumulat_spike_id", "date_time", "celsius", "status"]
        ]
        return filtered_df

    def add_last_spike_check(self, df_filtered):
        """returns dataframe where last spike of the day is defined as True"""
        df_filtered["last_spike_of_day"] = df_filtered[
            "date_time"
        ].dt.date != df_filtered["date_time"].dt.date.shift(-1)
        return df_filtered

    def prepare_24hr_window_start(self, df):
        """returns dataframe where the 24hr window start (based on the last spike of the day) is
        defined"""
        df["24hr_window_start"] = (df["date_time"] - pd.Timedelta(hours=24)).dt.floor(
            "s"
        )
        return df

    def filter_by_last_spike(self, df):
        df_last_spike_of_day = df[df["last_spike_of_day"]][
            ["cumulat_spike_id", "date_time", "last_spike_of_day", "24hr_window_start"]
        ]
        return df_last_spike_of_day

    def spike_duration_in_24hr_window(self, row, temp_data):
        mask = (
            (temp_data["date_time"] >= row["24hr_window_start"])
            & (temp_data["date_time"] <= row["date_time"])
            & (temp_data["status"].isin(["too_high", "too_low"]))
        )

        filtered = temp_data.loc[mask].copy()
        if filtered.empty:
            return 0
        return filtered["reading_gap_mins"].sum()

    def determine_spike_duration_24hr_mins(self, df_last_spike, df_original):
        df_last_spike["spike_duration_24hr_mins"] = df_last_spike.apply(
            self.spike_duration_in_24hr_window, axis=1, temp_data=df_original
        )
        return df_last_spike

    def get_extremes_info(self, df):
        df_extremes = (
            df[df["status"].isin(["too_high", "too_low"])]
            .groupby("cumulat_spike_id")
            .agg(
                extreme_temp=("celsius", lambda x: get_extreme_temp(x)),
                spike_date=("date_time", lambda x: x.dt.floor("D").min()),
                extreme_date_time=("date_time", lambda x: get_extreme_date_time(x, df)),
                spike_duration_mins=("date_time", lambda x: get_spike_duration(x)),
            )
        )
        return df_extremes

    def prepare_excursions_df(self, df_total_spike_duration, df_excursions):
        df_filtered = df_total_spike_duration[
            ["cumulat_spike_id", "spike_duration_24hr_mins"]
        ]
        df_merged = df_excursions.merge(df_filtered, on="cumulat_spike_id", how="left")
        return df_merged

    def renumber_spikes(self, df):
        date_filter = df["spike_date"]
        df.insert(
            loc=0,
            column="spike_number",
            value=df.groupby(date_filter).cumcount() + 1,
        )
        df.drop("cumulat_spike_id", axis=1, inplace=True)
        return df

    def check_against_limits(self, df, single_spike_duration, total_spikes_duration):
        mask = (df["spike_duration_mins"] > single_spike_duration) | (
            df["spike_duration_24hr_mins"] > total_spikes_duration
        )
        df.loc[mask, "spike_status"] = "Fail"
        df.loc[df["spike_status"] != "Fail", "spike_status"] = "Pass"
        return df

    def find_mkt(self, df_excursions, original_df):
        df_excursions["mkt"] = df_excursions.apply(
            self.calculate_mkt_24hr_window, df=original_df, axis=1
        )
        return df_excursions

    def calculate_mkt_24hr_window(self, row, df):
        window_start = row["extreme_date_time"] - timedelta(hours=12)
        window_end = row["extreme_date_time"] + timedelta(hours=12)

        mask = (row["spike_status"] == "Fail") & (
            (df["date_time"] <= window_end) & (df["date_time"] >= window_start)
        )

        filtered_df = df.loc[mask].copy()
        return self.apply_arrhenius(filtered_df)

    def apply_arrhenius(self, filtered_df):
        delta_H = 83.144
        R_constant = 0.0083144

        filtered_df["mkt_temp_variable"] = np.exp(
            -delta_H / (R_constant * (filtered_df["celsius"] + 273.15))
        )
        sum_mkt_temp_variables = filtered_df["mkt_temp_variable"].sum()
        if len(filtered_df) == 0:
            return None
        mkt = (delta_H / R_constant) / (
            -math.log(sum_mkt_temp_variables / len(filtered_df))
        ) - 273.15
        mkt = round(mkt, 1)
        return mkt

    def prepare_spike_summary_for_reporting(self, df_excursions, metadata):
        df_excursions["mkt"] = df_excursions["mkt"].fillna("Not applicable")
        df_excursions["spike_duration_24hr_mins"] = df_excursions[
            "spike_duration_24hr_mins"
        ].fillna("Not applicable")
        data = extract_to_list(df_excursions)
        data_with_header = insert_metadata_header(data, metadata)
        return data_with_header
