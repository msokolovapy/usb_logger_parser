from helper_functions import parse_
class AnalyticalService():
    def __init__(self):
        pass

    def analyze_spikes(self, storage_units):
        spike_dict_list = []
        for unit in storage_units:
            df = self.add_status_column(unit.temp_data, unit.low_alarm, unit.high_alarm)
            df = self.add_cumulat_spike_id(df)
            spike_dict = self.add_gap_mins(df)
            spike_dict_list.append(spike_dict)
        return spike_dict_list

    def add_status_column(self, df, low_alarm, high_alarm):
        df = df.copy()
        df.loc[df['celsius']> high_alarm, 'status'] = 'too_high'
        df.loc[df['celsius']< low_alarm, 'status'] = 'too_low'
        return df

    def add_cumulat_spike_id(self, df):
        df = df.copy()
        df['cumulat_spike_id'] = (df['status'] != df['status'].shift()).cumsum()
        return df

    def add_gap_mins(self, df):
        pass


