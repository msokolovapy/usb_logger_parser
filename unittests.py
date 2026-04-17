import unittest
from unittest.mock import Mock
from unittest.mock import patch
import pandas as pd
from app import logger
from storage_units import StorageCondition, Fridge, create_storage_condition_manually
from helper_functions import read, parse_, get_user_confirmation, validate_, get_average_temp
from analytical_service import AnalyticalService



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



class TestColdChainUnit(unittest.TestCase):
	def setUp(self):
		self.df_temp_data = SAMPLE_DF
		self.logger_id = 'ACPL01'
		self.serial_numb = '00001'
		self.file_basename = 'ACPL234_ACPL01_09Apr2026'
	def tearDown(self):
		pass
	
	@patch('storage_units.create_storage_condition_manually')
	@patch('storage_units.get_user_confirmation')
	@patch('storage_units.get_average_temp')
	@patch('storage_units.read')
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


class TestAnalyticalServiceInit(unittest.TestCase):
	def test_analyt_service_init(self):
		analytical_service = AnalyticalService()
		self.assertIsNotNone(analytical_service.analyze_spikes)

class TestAnalyzeSpikes(unittest.TestCase):
	def setUp(self):
		self.analytical_service = AnalyticalService()
	def tearDown(self):
		pass
	def test_analyze_spikes(self):
		storage_units = [Mock(), Mock()]
		spike_dict_list = self.analytical_service.analyze_spikes(storage_units)
		for dict in spike_dict_list:
			with self.subTest(dict):
				self.assertEqual(list(dict.items()), [('dict_key',1)])
	def test_add_status_column(self):
		temp_data = Mock()
		temp_data_copy = self.analytical_service.add_status_column(temp_data)
		self.assertIsNot(temp_data, temp_data_copy)


		


		

if __name__ == '__main__':
	unittest.main()














