
class AnalyticalService():
    def __init__(self):
        pass

    def analyze_spikes(self, storage_units):
        spike_dict_list = []
        for unit in storage_units:
            spike_dict = self.add_status_column(unit.temp_data)
            spike_dict = {'dict_key': 1}
            spike_dict_list.append(spike_dict)
        return spike_dict_list

    def add_status_column(self, temp_data):
        temp_data_c = temp_data.copy()
        
        return temp_data_c
