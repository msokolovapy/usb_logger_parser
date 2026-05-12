import os
from statistics import mean, median
import math
from collections import defaultdict
from datetime import datetime, date
from datetime import timedelta
from collections import Counter
from xlsxwriter import Workbook
import logging
import pandas as pd


FILE_1 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL228\Nov 2025\ACPL149_ACPL228.txt'
FILE_2 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL170\2025\ACPL149_ACPL170.txt'
FILE_3 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL64\2021\ACPL64-ACPL81.txt'
FILE_4 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL156\2020\ACP169_30-03-2020.txt'
FILE_5 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL156\2020\FG 018_30-03-2020.txt'
FILE_6 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL230\Oct 2023\ACPL262.txt'
FILE_7 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL329\Initial 2025\ACPL149_ACPL329.txt'
FILE_8 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL14\2021 Oct\ACPL14-ACPL88.txt'


logging.basicConfig(
    level=logging.INFO,
     format='%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler() 
    ]
)

logger = logging.getLogger(__name__)

	
class TemperatureData():
	"""This class stores temperature data obtained via Lascar USB data logger"""
	def __init__(self, logger_id,serial_no, df, file_basename):
		self._original_data = df
		self._logger = USBLogger(logger_id, serial_no)
		self._file_basename = file_basename 
		self._data_coll_freq = self.determine_ave_data_coll_frequency()
		self._data_matrix_size = df.shape

	@classmethod
	def read_from(cls,file_path):
		file_basename = os.path.basename(file_path)
		df = pd.read_csv(file_path, encoding='latin-1',
			dtype={'Serial Number': str,'Celsius(°C)': float,
				'High Alarm': float,'Low Alarm': float},
				converters = {'Time': pd.to_datetime})
		df = df.rename(columns={'Time':'date_time',
				'Celsius(°C)':'celsius',
				'High Alarm':'high_alarm',
				'Low Alarm':'low_alarm',
				'Serial Number':'serial_number'}
				)

		logger_id, serial_no = obtain_logger_info_from(df)
		return cls(logger_id,serial_no, df, file_basename)

	
	def determine_ave_data_coll_frequency(self):
		time_diff = self._original_data['date_time'] - self._original_data['date_time'].shift()
		ave_data_collect_freq = time_diff.mean().total_seconds()
		return ave_data_collect_freq


	def _analyze_spikes_(self, date):
		try:
			if self._spikes[date]:
				spikes = self._spikes.copy()
				if not self._total_spike_duration_acceptable(date,spikes):
					spikes[date]['total_spike_duration_out_of_range'] = 'yes'
				else:
					spikes[date]['total_spike_duration_out_of_range'] = 'no'

				for spike_info in spikes[date]['individual_spikes']:
					if (not self._single_spike_duration_acceptable(spike_info['spike_duration'])
						or not self._extreme_spike_temperature_acceptable(spike_info['extreme_spike_temp'])):
							spike_info['spike_out_of_range'] = 'yes'
					else:
						spike_info['spike_out_of_range'] = 'no'
				if 'total_spike_duration_out_of_range' in spikes[date] or 'spike_out_of_range' in [spike_info for spike_info in spikes[date]['individual_spikes']]:
					mkt = self._calculate_daily_MKT_for_(date)
					spikes[date]['mkt'] = mkt
				return spikes
			return None		
		except Exception as e:
			print(e)


	def _total_spike_duration_acceptable(self, date,spikes):
		if int(spikes[date]['total_spikes_duration'].total_seconds()) > Limits.limits[self._owner._storage_condition]['total_spike_duration']:
			return False


	def _single_spike_duration_acceptable(self, spike_info):
		spike_info = int(spike_info.total_seconds())
		if spike_info > Limits.limits[self._owner._storage_condition]['single_spike_duration']:
			return False

	def _extreme_spike_temperature_acceptable(self, spike_info):
		if spike_info['extreme_spike_temperature'] > Limits.limits[self._storage_condition]['high_alert'] or spike_info['extreme_spike_temperature'] < Limits.limits[self.owner._storage_condition]['low_alert']:
			return False

	
	def _calculate_daily_MKT_for_(self,formatted_date, delta_h=83.144):
		#calculates daily Mean Kinetic Temperature (MKT)
		daily_data = self._extract_temps_for_(formatted_date)
		temps = [dict['celsius'] for dict in daily_data]
		R = 0.008314
		temps_k = [t + 273.15 for t in temps]
		n = len(temps_k)
		sum_exp = sum(math.exp(-delta_h / (R * t)) for t in temps_k)
		mkt_k = - delta_h / (R * math.log(sum_exp / n))
		return round(mkt_k - 273.15,2)

	@property
	def df(self):
		return self._original_data
	@property
	def file_basename(self):
		return self._file_basename
	@property
	def data_matrix_size(self):
		return self._data_matrix_size
	@property
	def data_coll_freq(self):
		return self._data_coll_freq


class USBLogger():
	def __init__(self, logger_id, serial_no):
		self._id = logger_id
		self._serial_number = serial_no
		self._storage_condition = self._check_storage_condition()

	def prepare_for_reporting(self):
		#inserts additional data fields to the temp data for better readability when using xlsx report
		copy_temp_data = [tuple(data_point.values()) for data_point in self._data.original_data]
		data_width = self._data.data_matrix_size['data_width'] 

		header = self.prepare_header(data_width)
		column_names = self.prepare_column_names(data_width)
		
		copy_temp_data.insert(0,column_names)	
		for element in header:
			copy_temp_data.insert(0, element)
		return copy_temp_data

	def prepare_column_names(self, data_width):
		#returns column names for xlsx report such as 'row_numb', 'date_time', 'celsius' based on required data width
		column_names = list(self._data.original_data[0].keys())[:data_width]
		column_names = tuple(column_names)
		return column_names

	def prepare_header(self, data_width):
		header = [self._id, self._serial_number] #logger metadata allows easy logger data identification when multiple logger data traces are overlayed in xlsx report
		padded_header = pad_header_with_Nones(header,data_width)
		return padded_header
	
	def _check_storage_condition(self):
		storage_condition = input(f'Please specify which storage conditions this logger "{self._id}" was used to monitor? Enter either C (cold storage, hplc fridge), or FG (fridge), or FZ (freezer), or 25C (25°C), or 50C (50°C): ')
		storage_condition = storage_condition.upper()
		return storage_condition
	
	@property
	def id(self):
		return self._id
	@property
	def serial_number(self):
		return self._serial_number
	@property
	def storage_condition(self):
		return self._storage_condition
	


class Limits():
	limits = {'C': {'low_alarm': -10.0, 'high_alarm': 10.0, 'low_alert': -20.0, 'high_alert':-20.0, 'single_spike_duration':3600, 'total_spike_duration': 10800},
		   	'FG': {'low_alarm': 2.0, 'high_alarm': 8.0,'low_alert': 0.0, 'high_alert': 15.0, 'single_spike_duration':3600, 'total_spike_duration':10800},
			'FZ': {'low_alarm': -25.0, 'high_alarm': -15.0,'low_alert': -30.0, 'high_alert': -0.1, 'single_spike_duration':3600, 'total_spike_duration':10800},
			'25C': {'low_alarm': 24.0, 'high_alarm': 26.0,'low_alert': 15.0, 'high_alert': 30.0, 'single_spike_duration':900, 'total_spike_duration':10800},
			'50C': {'low_alarm': 45.0, 'high_alarm': 55.0,'low_alert': 25.0, 'high_alert': 60.0, 'single_spike_duration':900, 'total_spike_duration':10800}
	}


class AnalyticalService():
	def __init__(self,valid_files):
		self._files = valid_files

	@classmethod
	def create_from_(cls,file_list):
		valid_files = AnalyticalService.validate_(file_list)
		return cls(valid_files)		
	
	@classmethod
	def validate_(cls,file_list):
		valid_files = []
		for file in file_list:
			try:
				df = pd.read_csv(file,encoding='latin-1')
				if df.empty:
					logger.warning(f"Empty dataframe when trying to load {file}")
			except FileNotFoundError:
				logger.error(f"No file '{file}' found")
			except Exception as e:
				logger.exception(f"Unexpected error ({e})occured when trying to load {file}")
		required_columns = ["Time", "Celsius(°C)"]
		missing_columns = set(required_columns) - set(df.columns.values())
		if missing_columns:
			logger.warning(f"Some columns are missing: {missing_columns}")
		for column in required_columns:
			if df[column].isna().any():
				logger.warning(f"Some values are missing in {column}")
			file.append(valid_files)
		if valid_files:
			return valid_files
		logger.warning(f"No valid data files were provided")

	def get_files(self):
		return self._files

	def analyze_spikes(self, temp_data):
		spike_dict = self.prepare_spike_dict(temp_data)
		spike_dict = self.check_against_limits(spike_dict)
		spike_dict = self.add_mkt(spike_dict)
		return spike_dict


	def prepare_spike_dict(self, temp_data):
		temp_data = temp_data.copy()
		temp_data = self._add_status_column(temp_data)
		temp_data = self._add_cumulat_id(temp_data)
		temp_data_grouped = self._group_data_per_spike(temp_data)
		temp_data_grouped = self._add_spike_duration(temp_data_grouped)
		temp_data_grouped = self._reindex(temp_data_grouped)
		temp_data_grouped = self._add_extreme_temp_idx(temp_data_grouped)
		temp_data_grouped = self._add_extreme_temp(temp_data,temp_data_grouped)
		temp_data_grouped = self._add_extreme_date_time(temp_data,temp_data_grouped)
		excursions = self._summarize_(temp_data_grouped)
		return excursions

	def _add_status_column(self, temp_data):
		"""Find spikes and add 'status' column, which will be used to filter spike max (if too_high) or min (if too_low) temperature"""
		for data in temp_data:
			high_alarm = Limits.limits[data.logger.storage_condition]['high_alarm']
			low_alarm = Limits.limits[data.logger.storage_condition]['low_alarm']
			data.df.loc[temp_data['celsius'] > high_alarm, 'status'] = 'too_high'
			data.df.loc[temp_data['celsius'] < low_alarm, 'status'] = 'too_low'
		return temp_data	

	def _add_cumulat_id(self,temp_data):
		"""Adds cumulative spike id to enable initial numbering of spikes"""
		for data in temp_data:
			data.df['cumulat_spike_id'] = (data.df['status'] != data.df['status'].shift()).cumsum()
		return temp_data
	
	def _group_data_per_spike(self,temp_data):
		"""Groups temperature data for each spike found"""
		for data in temp_data:
			data = data.df[data.df['status'].isin(['too_high', 'too_low'])].groupby('cumulat_spike_id').agg(
    																	spike_status=('status','first'),
    																	spike_max_temp=('celsius', 'max'),
   																	spike_min_temp=('celsius', 'min'),
    																	spike_max_temp_id = ('celsius','idxmax'),
    																	spike_min_temp_id = ('celsius', 'idxmin'),
    																	spike_start_time=('date_time', 'min'),
 		   															spike_end_time=('date_time', 'max')
																	)
		return temp_data

# 	def  _add_spike_duration(self,temp_data):
# 		"""Finds spike duration in minutes"
# 		for data in temp_data:
# 			data.df['spike_duration_mins'] = ((data.df['spike_end_time'] - data.df['spike_start_time']).dt.total_seconds() / 60).astype(int)
# 		return temp_data

# 	def _reindex(self,temp_data):
# 		"""Adds spike id (consecutive number starting at 1) to be used instead of cumulative spike id (which is essentially a random number starting at 1)"""
# 		for data in temp_data:
# 			data.df['spike_id'] = data.df.groupby('cumulat_spike_id').ngroup() + 1
# 		return temp_data

# 	def _add_extreme_temp_idx(self,temp_data):
# 		"""Initiates id column for extreme temperature at which spike was observed"""
# 		for data in temp_data:
# 			data.df['extreme_idx'] = data.df['spike_max_temp_id'] #randomly set to spike_max_temp_id
# 			data.df.loc[data.df['spike_status'] == 'too_low', 'extreme_idx'] = data.df['spike_min_temp_id'] #re-write extreme id column values for when spike status is 'too_low'
# 		return temp_data

# 	def _add_extreme_temp(self, temp_data,temp_data_grouped):
# 		"""Retrieves extreme spike temperature and date/time stamp using extreme id"""
# 		for data in temp_data_grouped:
# 			data.df['extreme_temp'] = temp_data.loc[temp_data_grouped['extreme_idx'], 'celsius'].values
# temp_data_grouped['extreme_date_time'] = temp_data.loc[temp_data_grouped['extreme_idx'], 'date_time'].values

# #retrieve only relevant columns from temp_data_grouped:
# excursions = pd.DataFrame({'spike_numb':temp_data_grouped['spike_id'].values,
#                            'spike_extreme_temp': temp_data_grouped['extreme_temp'].values,
#                             'spike_extreme_date_time':temp_data_grouped['extreme_date_time'].values,
#                              'spike_duration_mins': temp_data_grouped['spike_duration_mins'].values})
# excursions = excursions.to_dict('records')
# 	def calculate_24hr_total_spike_duration(self, spike_dict):
# 		return None

# class SpikeDict():
# 	def __init__(self, date, daily_total_spikes_duration, 24hrs_total_spikes_duration = None, spikes_info):
# 		self._date = date
# 		self._daily_total_spikes_duration = daily_total_spikes_duration
# 		self._24hrs_total_spikes_duration = 24hrs_total_spikes_duration
# 		self._spikes_info = spikes_info
		
# 	def get_summary(self):
# 		return self._spikes_info

# 	def get_spike_duration(self, spike_numb = spike_numb):
# 		return self._spikes_info[spike_numb]['spike_duration_mins']

# 	def get_spike_temp(self,spike_numb = spike_numb):
# 		return self._spikes_info[spike_numb]['spike_extreme_temp'

# 	def get_mkt(self,spike_numb = spike_numb):
# 		return self._spikes_info[spike_numb]['mkt']	

# 	@property
# 	def date(self):
# 		return self._date
# 	@property
# 	def daily_total_duration(self):
# 		return self._daily_total_spikes_duration


#spikes.daily_total_duration
#spikes.date
#spikes.get_spike_temp(spike_numb = 1)
#spikes.get_spike_duration(spike_numb = 2)
#spikes.get_summary
#spikes.get_mkt(spike_numb = 2)

class ReportingService():
	pass



		
def main():
	file_list = []
	reporting_service = ReportingService()
	analytical_service = AnalyticalService()
	storage_units = [StorageCondition.create_from_(file) for file in files]
	spike_dicts = analytical_service.analyze_spikes(storage_units)
	xlsx_spike_reports = reporting_service.report_spike_dict_(spike_dicts)
	xlsx_data_reports = reporting_service.report_data_(storage_units)





#___________________________________________________________________________________________________________________
#	HELPER FUNCTIONS BELOW:

def data_collection_frequency_check(usb_loggers):
	frequencies = [logger.data.data_coll_freq for logger in usb_loggers]
	most_common = Counter(frequencies).most_common()[0][0]
	for i, logger in enumerate(usb_loggers):
		if logger.data.data_coll_freq != most_common:
			print(f"Logger {logger.id} is an outlier: its data collection frequency is {logger.data._data_coll_freq} as compared to most common frequency of {most_common}\nRemove this logger and try again")
			return None
	return True


def obtain_logger_info_from(df):
	id = df.columns[0]
	serial_no = df['serial_number'][0]
	return id, serial_no


def pad_header_with_Nones(header,data_width):
	number_Nones = data_width - 1
	padded_header = []
	for logger_metadata in header:
		padded_element = []
		padded_element.append(logger_metadata)
		for _ in range(number_Nones):
			padded_element.append(None)	
		padded_header.append(tuple(padded_element))
	return padded_header

def get_data_start_end(logger_data, column_names):
	#uses column names to extract starting and ending data row indices and adjusts row_min for xlsxwriter. Data starts immediately after column names
	row_min = logger_data.index(column_names) + 1
	row_max = len(logger_data)
	return row_min, row_max

def update_(date,spikes,spike_no):
	if spikes and spike_no:
		print(spikes)
		spikes[date]['individual_spikes'].append({'spike_out_of_range': 'Yes'})
		print(f'spikes after updating {spikes}')
	else:
		return None

#____________________________________________________________________________________________________________________________________________________

if __name__ == '__main__':	
	# file_list = [FILE_1,FILE_2,FILE_3,FILE_5,FILE_6,FILE_7,FILE_8]
	SPIKE_FILE = r'C:\Users\User\Desktop\Misc\usb_logger_parser\ACP169_30-03-2020_artificial_spikes.txt'
	file_list = [SPIKE_FILE]
	usb_loggers = [USBLogger.read_from(file) for file in file_list]
	for logger in usb_loggers:
		spikes = logger.data.prepare_spike_dict_()
		print(spikes)

	# report = XLSXReport.create_from(usb_loggers)
	# report.insert_data()
	# report.insert_graph()