import unittest
from unittest.mock import patch
import pandas as pd
from dataclasses import dataclass
import logging
import os

logging.basicConfig(
    level=logging.INFO,
     format='%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler() 
    ]
)

logger = logging.getLogger(__name__)

SAMPLE_DF = pd.DataFrame({
    "ACP169 BU_FZ156": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],
    "Time": [
        "2020-03-16 10:30:00",
        "2020-03-16 10:40:00",
        "2020-03-16 10:50:00",
        "2020-03-16 11:00:00",
        "2020-03-16 11:10:00",
        "2020-03-16 11:20:00",
        "2020-03-16 11:30:00",
        "2020-03-16 11:40:00",
        "2020-03-16 11:50:00",
        "2020-03-16 12:00:00",
        "2020-03-16 12:10:00",
        "2020-03-16 12:20:00",
        "2020-03-16 12:30:00",
        "2020-03-16 12:40:00",
        "2020-03-16 12:50:00",
        "2020-03-16 13:00:00",
        "2020-03-16 13:10:00",
        "2020-03-16 13:20:00",
        "2020-03-16 13:30:00",
        "2020-03-16 13:40:00",
    ],
    "Celsius(°C)": [0.0,0.5,1.0,1.5,2.0,2.5,3.5,4.5,5.0,6.0,7.0,10.0,9.0,8.0,8.5,7.0,7.3,6.0,5.5,5.0],
    "High Alarm": [-4.5] * 20,
    "Low Alarm":  [-25.5] * 20,
    "Serial Number": ["052297777"] + [None] * 19,
})


def read(file):
	valid_file = validate_(file)
	df= pd.read_csv(valid_file, encoding = 'latin-1')
	df_temp_data,logger_id, serial_numb = parse_(df) 
	file_basename = os.path.basename(file)
	return df_temp_data,logger_id, serial_numb, file_basename

def get_average_temp():
	pass

def parse_(df):
		df.rename(columns={'Time': 'date_time',
			'Celsius(°C)':'celsius',
			'High Alarm':'high_alarm',
			'Low Alarm':'low_alarm',
			'Serial Number':'serial_number'
			}, inplace=True)
		logger_id = df.columns.values[0]
		serial_numb = df['serial_number'][0]
		df.drop(columns=[logger_id, "serial_number"], inplace=True)
		return df, logger_id, serial_numb
		


def get_user_confirmation():
	user_input = input("It looks like your temperature trace '{file_basename}' for logger {logger_id}\
						may have come from either cold storage or fridge.\
						Please confirm here (FG/CS):" 
				)
	return user_input


class StorageCondition():
	@classmethod
	def create_from_(cls, file):
		df_temp_data,logger_id, serial_numb, file_basename = read(file) #MUST include data validation and re-naming of columns
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

def validate_(file_list):
	valid_files = []
	for file in file_list:
		try:
			df = pd.read_csv(file, encoding='latin-1')
			if df.empty:
				logger.warning(f"Empty dataframe when trying to load {file}")
		except FileNotFoundError:
			logger.error(f"No file '{file}' found")
		except Exception as e:
			logger.exception(f"Unexpected error ({e})occured when trying to load {file}")
		
		required_columns = ["Time", "Celsius(°C)"]
		missing_columns = set(required_columns) - set(df.columns)
		if missing_columns:
			logger.warning(f"Some columns are missing: {missing_columns}")
		for column in required_columns:
			if df[column].isna().any():
				logger.warning(f"Some values are missing in '{column}' column")
			valid_files.append(file)
		if valid_files:
			return valid_files
		logger.warning(f"No valid data files were provided")
		

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


class TestColdChainUnit(unittest.TestCase):
	def setUp(self):
		self.df_temp_data = SAMPLE_DF
		self.logger_id = 'ACPL01'
		self.serial_numb = '00001'
		self.file_basename = 'ACPL234_ACPL01_09Apr2026'
	def tearDown(self):
		pass
	
	@patch(f'{__name__}.create_storage_condition_manually')
	@patch(f'{__name__}.get_user_confirmation')
	@patch(f'{__name__}.get_average_temp')
	@patch(f'{__name__}.read')
	def test_create_cc_unit(self,mock_read, mock_get_ave_temp, mock_user_confirmation, mock_manual_create):
		file = 'dummy.txt'
		mock_read.return_value = (self.df_temp_data, self.logger_id, self.serial_numb, self.file_basename)
		mock_get_ave_temp.return_value = 5.0
		mock_user_confirmation.side_effect = ['abracadabra','FG']
		mock_manual_create.return_value = Fridge(self.df_temp_data, self.logger_id, self.serial_numb, self.file_basename)
			
		fridge = StorageCondition.create_from_(file)
		self.assertIsNotNone(fridge)
		self.assertEqual(fridge.low_alarm, 2.0)
		self.assertEqual(fridge.high_alarm, 8.0)
		self.assertEqual(fridge.spike_duration, 3600)
		self.assertEqual(fridge.logger.id, 'ACPL01')
		self.assertEqual(fridge.logger.serial_numb, '00001')
		self.assertEqual(fridge.temp_data.shape, (20,6))
		self.assertEqual(fridge.metadata, 'ACPL234_ACPL01_09Apr2026')

class TestHelperFunctions(unittest.TestCase):
	def setUp(self):
		self.df_temp_data = SAMPLE_DF
		self.logger_id = 'ACPL01'
		self.serial_numb = '00000001'
		self.file_basename = 'ACPL234_ACPL01_09Apr2026'
	def tearDown(self):
		pass

	@patch("builtins.input")
	def test_create_storage_condition_manually(self, mock_input):
		mock_input.side_effect = ['abracadabra', 'FG']
		storage_condit = create_storage_condition_manually(self.df_temp_data, self.logger_id, self.serial_numb, self.file_basename)
		self.assertIsNotNone(storage_condit)
		self.assertEqual(storage_condit.high_alert, 15.0)

	def test_parse_(self):
		pass


	@patch('os.path.basename')
	@patch(f'{__name__}.validate_')
	@patch(f'{__name__}.pd.read_csv')
	def test_read(self, mock_read_csv, mock_valid_data, mock_basename):
		mock_valid_data.return_value = 'dummy.txt'
		mock_read_csv.return_value = pd.DataFrame(self.df_temp_data)
		mock_basename.return_value = self.file_basename
		expected_column_names = ['date_time', 'celsius', 'high_alarm', 'low_alarm']
		
		df_temp_data,logger_id, serial_numb, file_basename = read('dummy.txt')
		
		self.assertEqual(logger_id, "ACP169 BU_FZ156")
		self.assertEqual(serial_numb,"052297777")
		self.assertEqual(list(df_temp_data.columns), expected_column_names)

		

if __name__ == '__main__':
	unittest.main()














