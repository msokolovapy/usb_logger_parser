from dataclasses import dataclass
from src.usb_logger_parser.helper_functions import read, get_average_temp, get_user_confirmation

class StorageCondition():
	@classmethod
	def create_from_(cls, file):
		df_temp_data,logger_id, serial_numb, file_basename = read(file)
		average_temp = get_average_temp(df_temp_data)
		if Limits.fridge.low_alarm <= average_temp <= Limits.fridge.high_alarm:
			while True:
				user_input = get_user_confirmation()
				if user_input == 'FG':
					return Fridge(df_temp_data,logger_id, serial_numb, file_basename)
				elif user_input == 'CS':
					return ColdStorage(df_temp_data,logger_id, serial_numb, file_basename)
				else:
					print('Please either enter FG or CS')
					continue
		elif Limits.freezer.low_alarm <= average_temp <= Limits.freezer.high_alarm:
					return Freezer(df_temp_data,logger_id, serial_numb, file_basename)
		elif Limits.storage_25c.low_alarm <= average_temp <= Limits.storage_25c.high_alarm:
					return TwentyFiveCelsius(df_temp_data,logger_id, serial_numb, file_basename)
		elif Limits.storage_50c.low_alarm <= average_temp <= Limits.storage_50c.high_alarm:
					return FiftyCelsius(df_temp_data,logger_id, serial_numb, file_basename)
		else:
			return create_storage_condition_manually(df_temp_data,logger_id, serial_numb, file_basename)

def create_storage_condition_manually(df_temp_data,logger_id, serial_numb, file_basename):
	storage_condit_dict = {'FG': Fridge(df_temp_data,logger_id, serial_numb, file_basename)
				}
	while True:
		user_input = input("Storage condition not clear. Please clarify storage condition for your temperature trace '{file_basename}' for logger {logger_id} here (FG/FZ/CS/25C/50C):")
		if user_input in storage_condit_dict.keys():
			storage_condition = storage_condit_dict[user_input]
			return storage_condition
		else:
			storage_str = ('/ ').join(storage_condit_dict.keys())
			print(f'Please select storage condition from {storage_str}')
			continue
	

class Fridge(StorageCondition):
	def __init__(self, df_temp_data, logger_id, serial_numb, file_basename):
		self.low_alarm = Limits.fridge.low_alarm
		self.high_alarm = Limits.fridge.high_alarm
		self.low_alert = Limits.fridge.low_alert
		self.high_alert = Limits.fridge.high_alert 
		self.spike_duration = Limits.fridge.spike_duration
		self.total_spikes_duration = Limits.fridge.total_spikes_duration
		self.temp_data = df_temp_data
		self.logger = USBLogger(id = logger_id, serial_numb = serial_numb)
		self.metadata = file_basename
	
	
@dataclass
class USBLogger:
	id : str
	serial_numb : str


@dataclass
class LimitValues:
    low_alarm:float
    high_alarm:float
    low_alert:float
    high_alert:float
    spike_duration:int
    total_spikes_duration:int


class Limits:
    fridge = LimitValues(2.0,   8.0,  0.0,  15.0, 3600, 10800)
    freezer = LimitValues(-25.0, -15.0, -30.0, -0.1, 3600, 10800)
    cold_storage = LimitValues(-10.0,  10.0, -20.0,  20.0, 3600, 10800)
    storage_25c = LimitValues(24.0,  26.0,  15.0,  30.0,  900, 10800)
    storage_50c = LimitValues(45.0,  55.0,  25.0,  60.0,  900, 10800)