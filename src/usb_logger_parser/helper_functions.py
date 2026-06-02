import pandas as pd
import os
import sys
import logging
from collections import Counter

logger = logging.getLogger(__name__)


def read(file):
    valid_file = validate_(file)
    df = pd.read_csv(
        file,
        encoding="latin-1",
        dtype={
            "Serial Number": str,
            "Celsius(°C)": float,
            "High Alarm": float,
            "Low Alarm": float,
        },
        converters={"Time": pd.to_datetime},
    )
    df_temp_data, logger_id, serial_numb = parse_(df)
    file_basename = os.path.basename(file)
    return df_temp_data, logger_id, serial_numb, file_basename


def get_average_temp(df):
    return df["celsius"].mean()


def parse_(df):
    df = df.copy()
    df.rename(
        columns={
            "Time": "date_time",
            "Celsius(°C)": "celsius",
            "High Alarm": "high_alarm",
            "Low Alarm": "low_alarm",
            "Serial Number": "serial_number",
        },
        inplace=True,
    )
    logger_id = df.columns.values[0]
    serial_numb = df["serial_number"][0]
    df.drop(columns=[logger_id, "serial_number"], inplace=True)
    return df, logger_id, serial_numb


def get_user_confirmation():
    user_input = input(
        "It looks like your temperature trace '{file_basename}' for logger {logger_id}\
						may have come from either cold storage or fridge.\
						Please confirm here (FG/CS):"
    )
    return user_input


def validate_(file):
    try:
        df = pd.read_csv(file, encoding="latin-1")
        if df.empty:
            logger.warning(f"Empty dataframe when trying to load {file}")
            raise ValueError(f"Empty dataframe when trying to load {file}")

        required_columns = ["Time", "Celsius(°C)"]
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            logger.warning(f"Some columns are missing: {(', ').join(missing_columns)}")
            raise KeyError(f"Some columns are missing: {(', ').join(missing_columns)}")

        for column in required_columns:
            if df[column].isna().any():
                logger.warning(f"Some values are missing in '{column}' column")
                raise ValueError(f"Some values are missing in '{column}' column")
        return file

    except FileNotFoundError:
        logger.error(f"No file '{file}' found")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error ({e}) occured when trying to load {file}")
        raise
    sys.exit(1)


def get_spike_duration(pandas_series_date_time):
    spike_duration = int(
        (pandas_series_date_time.max() - pandas_series_date_time.min()).total_seconds()
        / 60
    )
    return spike_duration


def get_extreme_date_time(pandas_series_date_time, df):
    filtered = df.loc[pandas_series_date_time.index, "celsius"]
    mask = filtered.abs().idxmax()
    extreme_date_times = pandas_series_date_time.loc[mask]
    return extreme_date_times


def get_extreme_temp(pandas_series_celsius):
    mask = pandas_series_celsius.abs().idxmax()
    return pandas_series_celsius.loc[mask]


def convert_timestamps(df):
    df["extreme_date_time"] = pd.to_datetime(df["extreme_date_time"]).dt.to_pydatetime()
    df["spike_date"] = pd.to_datetime(df["spike_date"]).dt.date
    return df


def data_collection_frequency_check(storage_units):
    if len(storage_units) == 1:
        return True  # test always passes for one storage unit as there is nothing to compare this one storage unit to
    freq_counter = Counter(unit.logger.ave_data_coll_freq for unit in storage_units)
    most_common_value = freq_counter.most_common()[0][0]
    for unit in storage_units:
        if unit.logger.ave_data_coll_freq != most_common_value:
            logger.warning(
                    f"Data frequency collection for logger {unit.logger.id} differs from the rest of the temperature data collected. To ensure meaningful comparison, remove logger {unit.logger.id} and try again"
            )
            raise ValueError(
                    f"Data frequency collection for logger {unit.logger.id} differs from the rest of the temperature data collected. To ensure meaningful comparison, remove logger {unit.logger.id} and try again"
                )
    return True


def get_ave_data_coll_freq(df):
    data_coll_freq_series = df['date_time'].diff()
    ave_data_coll_freq = round(data_coll_freq_series.mean().total_seconds() / 60, 6)
    return ave_data_coll_freq


