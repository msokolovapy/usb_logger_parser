from helper_functions import parse_
class AnalyticalService():
    def __init__(self):
        pass

    def analyze_spikes(self, storage_units):
        """returns spike information for each storage unit"""
        spike_dict_list = []
        for unit in storage_units:
            df = unit.temp_data.copy()
            df = self.add_status_column(df, unit.low_alarm, unit.high_alarm)
            df = self.add_cumulat_spike_id(df)
            df = self.add_gap_mins(df)
            spike_dict = {}
            spike_dict_list.append(spike_dict)
        return spike_dict_list

    def add_status_column(self, df, low_alarm, high_alarm):
        """finds spikes and adds 'status' column, which will be used to filter spike max (if too_high) or min (if too_low) temperature"""
        df.loc[df['celsius']> high_alarm, 'status'] = 'too_high'
        df.loc[df['celsius']< low_alarm, 'status'] = 'too_low'
        return df

    def add_cumulat_spike_id(self, df):
        """adds cumulative spike id for grouping spike information"""
        df['cumulat_spike_id'] = (df['status'] != df['status'].shift()).cumsum()
        return df

    def add_gap_mins(self, df):
        """groups spike info and finds delta datetime between readings within the group. Will be used to calculate total_spike_duration"""
        df['reading_gap_mins'] = df.groupby('cumulat_spike_id')['date_time'].diff().dt.total_seconds() / 60
        return df

    def prepare_df_last_spike_of_day(self, df):
        """returns dataframe where: last spike of the day is determined and 24hr window before the last spike is defined. Will be used to 
        determine total spikes duration"""
        df = self.filter(df)
        df = self.add_last_spike_check(df)
        df = self.prepare_24hr_window_start(df)
        df = self.group_data(df)
        return df

    def filter(self, df):
        filtered_df = df[df['status'].isin(['too_high', 'too_low'])][['cumulat_spike_id','date_time','celsius','status']]
        return filtered_df


    def add_last_spike_check(self, df_filtered):
        """returns dataframe where last spike of the day is defined as True if """
        df_filtered['last_spike_of_day'] = ((df_filtered['date_time'].dt.date != df_filtered['date_time'].dt.date.shift(-1)))
        return df_filtered

    def prepare_24hr_window_start(self, df):
        """returns dataframe where the 24hr window start (based on the last spike of the day) is
        defined"""
        df['24hr_window_start'] = pd.to_datetime(np.where(
                                                        df['last_spike_of_day'],
                                                        (df['date_time'] - pd.Timedelta(hours=24)).dt.floor('s'),
                                                        pd.NaT
                                                        ))
        return df

    def group_data(self,df):
        df_last_spike_of_day = df[df['last_spike_of_day']==True][['cumulat_spike_id','date_time','last_spike_of_day','24hr_window_start']]

        return df_last_spike_of_day

