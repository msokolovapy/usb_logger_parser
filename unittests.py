import unittest
from unittest.mock import Mock
from unittest.mock import patch
import pandas as pd
from pandas import Timestamp
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
		self.unit = Fridge(*parse_(SAMPLE_DF), 'dummy_txt')
	def tearDown(self):
		pass
	
	
	
	@patch('analytical_service.AnalyticalService.add_gap_mins')
	@patch('analytical_service.AnalyticalService.add_cumulat_spike_id')
	@patch('analytical_service.AnalyticalService.add_status_column')
	def test_analyze_spikes(self, mock_add_status, mock_cumulat_id, mock_gap_mins):
		storage_units = [Mock(temp_data = {'dummy_column': 'dummy_value'}, low_alarm = 'low_alarm', high_alarm = 'high_alarm')]
		mock_add_status.side_effect = ['df_added_status']
		mock_cumulat_id.side_effect = ['df_with_cumulat_spike_id']

		spike_dict_list = self.analytical_service.analyze_spikes(storage_units)

		mock_add_status.assert_called_with({'dummy_column': 'dummy_value'}, 'low_alarm', 'high_alarm')
		mock_cumulat_id.assert_called_with('df_added_status')
		mock_gap_mins.assert_called_with('df_with_cumulat_spike_id')

		for spike_dict in spike_dict_list:
			with self.subTest(dict):
				self.fail("FINISH TESTING .analyze_spikes !")

	def test_add_status_column(self):
		sample_df = pd.DataFrame({'date_time':["2020-03-15 10:20:00",
												"2020-03-15 10:30:00",
												"2020-03-15 10:40:00",
												"2020-03-16 10:30:00",
       											"2020-03-16 10:40:00",
												"2020-03-16 10:50:00",
												"2020-03-16 11:00:00",
												"2020-03-16 11:10:00",
												"2020-03-16 11:20:00",
												"2020-03-16 11:30:00",
												"2020-03-16 11:40:00"
												], 
												'celsius':[16.0,20.0,16.0,5.0,0.0,0.5,1.0,1.5,2.0,2.5,3.5]
												})
		df_added_status = self.analytical_service.add_status_column(sample_df, self.unit.low_alarm, self.unit.high_alarm)
		self.assertIn('status', df_added_status.columns)

	def test_add_cumulat_spike_id(self):
		sample_df = pd.DataFrame({'date_time':["2020-03-15 10:20:00",
												"2020-03-15 10:30:00",
												"2020-03-15 10:40:00",
												"2020-03-16 10:30:00",
       											"2020-03-16 10:40:00",
												"2020-03-16 10:50:00",
												"2020-03-16 11:00:00",
												"2020-03-16 11:10:00",
												"2020-03-16 11:20:00",
												"2020-03-16 11:30:00",
												"2020-03-16 11:40:00"
												], 
												'celsius':[16.0,20.0,16.0,5.0,0.0,0.5,1.0,1.5,2.0,2.5,3.5],
												'status': ['too_high', 'too_high', 'too_high', None, 
															'too_low', 'too_low', 'too_low', 'too_low', None, None, None]
												})
		df_cumulat_spike_id = self.analytical_service.add_cumulat_spike_id(sample_df)
		self.assertIn('cumulat_spike_id', df_cumulat_spike_id.columns)
		self.assertEqual(df_cumulat_spike_id['cumulat_spike_id'][0],1)

	def test_add_gap_mins(self):
		sample_df = pd.DataFrame({'date_time':["2020-03-15 10:20:00",
												"2020-03-15 10:30:00",
												"2020-03-15 10:40:00",
												"2020-03-16 10:30:00",
       											"2020-03-16 10:40:00",
												"2020-03-16 10:50:00",
												"2020-03-16 11:00:00",
												"2020-03-16 11:10:00",
												"2020-03-16 11:20:00",
												"2020-03-16 11:30:00",
												"2020-03-16 11:40:00"
												], 
												'cumulat_spike_id': [1, 1, 1, 2, 3, 3, 3, 3, 4, 5, 6],
												'status': ['too_high', 'too_high', 'too_high', None, 
															'too_low', 'too_low', 'too_low', 'too_low', None, None, None]
												})
		sample_df['date_time'] = pd.to_datetime(sample_df['date_time'])
		df = self.analytical_service.add_gap_mins(sample_df)

		self.assertIn('reading_gap_mins', df.columns)
		self.assertTrue((df['reading_gap_mins'] == 10).any())
		
	def test_prepare_df_last_spike_of_day(self):
		with patch.object(AnalyticalService, 'filter_by_status') as mock_status_filter,\
				patch.object(AnalyticalService, 'add_last_spike_check') as mock_last_spike,\
				patch.object(AnalyticalService, 'prepare_24hr_window_start') as mock_24hr_window,\
				patch.object(AnalyticalService, 'filter_by_last_spike') as mock_spike_filter,\
				patch.object(AnalyticalService, 'determine_spike_duration_24hr_mins') as mock_last_spike_df:
			mock_status_filter.return_value = 'df_filtered_by_status'
			mock_last_spike.return_value = 'last_spike_added'
			mock_24hr_window.return_value = '24hr_window_added'
			mock_spike_filter.return_value = 'df_filtered_by_last_spike'
			mock_last_spike_df.return_value = 'df_spike_duration_24hr_added'

			last_spike_df = self.analytical_service.prepare_df_last_spike_of_day('original_df')

			mock_status_filter.assert_called_with('original_df')
			mock_last_spike.assert_called_with('df_filtered_by_status')
			mock_24hr_window.assert_called_with('last_spike_added')
			mock_spike_filter.assert_called_with('24hr_window_added')
			mock_last_spike_df.assert_called_with('df_filtered_by_last_spike','original_df')

			self.assertEqual(last_spike_df, 'df_spike_duration_24hr_added')


	def test_filter_by_status(self):
		sample_df = pd.DataFrame({'date_time':["2020-03-15 10:20:00",
												"2020-03-15 10:30:00",
												"2020-03-15 10:40:00",
												"2020-03-16 10:30:00",
       											"2020-03-16 10:40:00",
												"2020-03-16 10:50:00",
												"2020-03-16 11:00:00",
												"2020-03-16 11:10:00",
												"2020-03-16 11:20:00",
												"2020-03-16 11:30:00",
												"2020-03-16 11:40:00"
												], 
												'celsius':[16.0,20.0,16.0,5.0,0.0,0.5,1.0,1.5,2.0,2.5,3.5],
												'status': ['too_high', 'too_high', 'too_high', None, 
															'too_low', 'too_low', 'too_low', 'too_low', 
															None, None, None],
												'cumulat_spike_id': [1, 1, 1, 2, 3, 3, 3, 3, 4, 5, 6]
												})

		df_filtered = self.analytical_service.filter_by_status(sample_df)
		self.assertTrue((df_filtered['status']!=None).all())
	
	def test_add_last_spike_check(self):
		sample_df = pd.DataFrame({'cumulat_spike_id': [1, 1, 1, 3, 3, 3, 3],
								 'date_time': ['2020-03-15 10:20:00', '2020-03-15 10:30:00', 
								 '2020-03-15 10:40:00', '2020-03-16 10:40:00', 
								 '2020-03-16 10:50:00', '2020-03-16 11:00:00', 
								 '2020-03-16 11:10:00'], 
								 'celsius': [16.0, 20.0, 16.0, 0.0, 0.5, 1.0, 1.5], 
								 'status': ['too_high', 'too_high', 'too_high', 'too_low', 'too_low', 'too_low', 'too_low']})
		sample_df['date_time'] = pd.to_datetime(sample_df['date_time'])
		
		df_last_spike = self.analytical_service.add_last_spike_check(sample_df)
		self.assertEqual(df_last_spike['last_spike_of_day'].to_list(), [False, False, True, False, False, False, True])

	def test_prepare_24hr_window_start(self):
		sample_df = pd.DataFrame({
								'cumulat_spike_id': [1, 1, 1, 3, 3, 3, 3],
								'date_time': [
								Timestamp('2020-03-15 10:20:00'), Timestamp('2020-03-15 10:30:00'),
								Timestamp('2020-03-15 10:40:00'), Timestamp('2020-03-16 10:40:00'),
								Timestamp('2020-03-16 10:50:00'), Timestamp('2020-03-16 11:00:00'), 
								Timestamp('2020-03-16 11:10:00')
								], 
							'celsius': [16.0, 20.0, 16.0, 0.0, 0.5, 1.0, 1.5], 
							'status': ['too_high', 'too_high', 'too_high', 'too_low', 'too_low', 'too_low', 'too_low'], 
							'last_spike_of_day': [False, False, True, False, False, False, True]})
		expected_values = [Timestamp('2020-03-14 10:20:00'), Timestamp('2020-03-14 10:30:00'),
						Timestamp('2020-03-14 10:40:00'), Timestamp('2020-03-15 10:40:00'), 
						Timestamp('2020-03-15 10:50:00'), Timestamp('2020-03-15 11:00:00'), 
						Timestamp('2020-03-15 11:10:00')]

		df_24hr_window = self.analytical_service.prepare_24hr_window_start(sample_df)
		self.assertEqual(df_24hr_window['24hr_window_start'].to_list(), expected_values)
	


	def test_filter_by_spike(self):
		sample_df = pd.DataFrame({
								'cumulat_spike_id': [1, 1, 1, 3, 3, 3, 3],
								'date_time': [
								Timestamp('2020-03-15 10:20:00'), Timestamp('2020-03-15 10:30:00'),
								Timestamp('2020-03-15 10:40:00'), Timestamp('2020-03-16 10:40:00'),
								Timestamp('2020-03-16 10:50:00'), Timestamp('2020-03-16 11:00:00'), 
								Timestamp('2020-03-16 11:10:00')
								], 
							'celsius': [16.0, 20.0, 16.0, 0.0, 0.5, 1.0, 1.5], 
							'status': ['too_high', 'too_high', 'too_high', 'too_low', 'too_low', 'too_low', 'too_low'], 
							'last_spike_of_day': [False, False, True, False, False, False, True],
							'24hr_window_start': [
								Timestamp('2020-03-14 10:20:00'), Timestamp('2020-03-14 10:30:00'), 
								Timestamp('2020-03-14 10:40:00'), Timestamp('2020-03-15 10:40:00'), 
								Timestamp('2020-03-15 10:50:00'), Timestamp('2020-03-15 11:00:00'), 
								Timestamp('2020-03-15 11:10:00')]
							})
		df_grouped = self.analytical_service.filter_by_last_spike(sample_df)
		expected_columns = ['cumulat_spike_id','date_time','last_spike_of_day','24hr_window_start']

		self.assertTrue((df_grouped['last_spike_of_day'] == True).all())
		self.assertEqual(list(df_grouped.columns),expected_columns)
		
	def test_determine_spike_duration_24hr_mins(self):
		sample_df_24hr_spikes = pd.DataFrame({'date_time':[Timestamp('2020-03-16 11:10:00')], '24hr_window_start': [Timestamp('2020-03-15 11:10:00')]})
		sample_df = pd.DataFrame({'date_time': [Timestamp('2020-03-15 10:20:00'), Timestamp('2020-03-15 10:30:00'), 
									Timestamp('2020-03-15 10:40:00'), Timestamp('2020-03-16 10:30:00'), 
									Timestamp('2020-03-16 10:40:00'), Timestamp('2020-03-16 10:50:00'), 
									Timestamp('2020-03-16 11:00:00'), Timestamp('2020-03-16 11:10:00'), 
									Timestamp('2020-03-16 11:20:00'), Timestamp('2020-03-16 11:30:00'), 
									Timestamp('2020-03-16 11:40:00')],
		'status': ['too_high', 'too_high', 'too_high', None, 'too_low', 'too_low', 'too_low', 'too_low', None, None, None], 
		'reading_gap_mins': [None, 10.0, 10.0, None, None, 10.0, 10.0, 10.0, None, None, None]})

		df = self.analytical_service.determine_spike_duration_24hr_mins(sample_df_24hr_spikes, sample_df)
		self.assertEqual(df['spike_duration_24hr_mins'].item(), 30.0)

		with patch.object(AnalyticalService,'spike_duration_in_24hr_window', return_value = 10.0, autospec = True) as mock_spike_duration:
			df = self.analytical_service.determine_spike_duration_24hr_mins(sample_df_24hr_spikes, sample_df)
			mock_spike_duration.assert_called_once()
			

			



		
		


		

if __name__ == '__main__':
	unittest.main()









