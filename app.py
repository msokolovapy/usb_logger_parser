import os
from statistics import mean, median
import math
from collections import defaultdict
from datetime import datetime, date
from datetime import timedelta
from collections import Counter
from xlsxwriter import Workbook


FILE_1 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL228\Nov 2025\ACPL149_ACPL228.txt'
FILE_2 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL170\2025\ACPL149_ACPL170.txt'
FILE_3 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL64\2021\ACPL64-ACPL81.txt'
FILE_4 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL156\2020\ACP169_30-03-2020.txt'
FILE_5 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL156\2020\FG 018_30-03-2020.txt'
FILE_6 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL230\Oct 2023\ACPL262.txt'
FILE_7 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL329\Initial 2025\ACPL149_ACPL329.txt'
FILE_8 = r'N:\GMP Quality Assurance\QA Accessible Documents\Data Logger Downloads\Temperature Mapping\ACPL14\2021 Oct\ACPL14-ACPL88.txt'
	
	
class TemperatureData():
	"""This class stores temperature data obtained via Lascar USB data logger"""
	def __init__(self, temperature_data, owner = None):
		self._original_data = temperature_data 
		self._owner = owner
		self._max = self.select_max_temperature()
		self._min = self.select_min_temperature()
		self._average = self.select_average_temperature()
		self._median = self.select_median_temperature()
		# self._low_alarm = None
		# self._high_alarm = None
		# self._storage_condition = None
		self._data_coll_freq = self.determine_ave_data_coll_frequency()
		self._data_matrix_size = {'data_width':len(self._original_data[0]),	'data_lenth':len(self._original_data)}
		self._spikes = defaultdict(lambda: defaultdict(list))
		self._anomalous_spikes = defaultdict(lambda: defaultdict(list))

	def select_max_temperature(self):
		return (max(row['celsius'] for row in self.original_data))
	def select_min_temperature(self):
		return (min(row['celsius'] for row in self.original_data))
	def select_average_temperature(self):
		return (round(mean(row['celsius'] for row in self.original_data),2))
	def select_median_temperature(self):
		return (median(row['celsius'] for row in self.original_data))
	
	def determine_ave_data_coll_frequency(self):
		time_diffs = list(self.get_time_diff())  # List of timedelta objects
		avg_timedelta = sum(time_diffs, timedelta()) / len(time_diffs)
		return avg_timedelta

	def get_time_diff(self):
		prev_timestamp = None
		for row in self._original_data:
			if prev_timestamp is not None:
				yield row['date_time'] - prev_timestamp
			prev_timestamp = row['date_time']

	# def add_low_high_alarms(self, storage_condition):
	# 	try:
	# 		self._low_alarm = Alarms.low_alarms[storage_condition]
	# 		self._high_alarm = Alarms.high_alarms[storage_condition]
	# 	except KeyError:
	# 		raise


	def _extract_temps_for_(self,date):
		try:
			extracted_temps = []
			for data_dict in self._original_data:
				if data_dict['date_time'].date() == date:
					extracted_temps.append(data_dict)
			return extracted_temps
		except Exception as e:
			return None
	
	def _extract_temp_spikes_for_(self, date):
		"""Prepares a dictionary of grouped data (date_time and Celsius reading) for each spike found"""	
		data = self._extract_temps_for_(date)
		spikes = defaultdict(lambda: defaultdict(list))
		spike_no = 0
		spike_flag = None

		if data:
			try:
				for data_dict in data:
					if Limits <= data_dict['celsius'] <= self._high_alarm:
						spike_flag = False
					else:
						if not spike_flag:	#checks if current spike data point belongs to next spike group
							spike_flag = True
							spike_no = spike_no + 1 
						spikes[date][spike_no].append((data_dict['date_time'],data_dict['celsius']))
				spikes = {k:dict(v) for k,v in spikes.items()} #turn to regular dictionary for easy viewing
				return spikes
			except Exception as e:
				return None
		else:
			return None
	
	def prepare_spike_dict_(self):
		date = input('Enter date for which spike/MKT analysis needs to be performed (note date format: dd-mm-yyyy):' )
		try:
			formatted_date = datetime.strptime(date,'%d-%m-%Y').date()
		except ValueError:
			print(f'You entered {date}. Ensure your entered date follows dd-mm-yyyy format and try again')

		if not formatted_date in self._spikes:
			spikes = self._extract_temp_spikes_for_(formatted_date)
			if spikes:
				total_spikes_duration = timedelta(hours=0, minutes=0, seconds=0)

				for spike_no, data_list in spikes[formatted_date].items():
					spike_temps = [celsius for (_,celsius) in data_list]
					spike_dates_times = [date_time for (date_time,_) in data_list]
		
					if all(temp < self._low_alarm for temp in spike_temps):
						spike_temp = min(spike_temps)
					elif all(temp > self._high_alarm for temp in spike_temps):
						spike_temp = max(spike_temps)
					else:
						self._anomalous_spikes[formatted_date][spike_no].append(data_list)
						print(f'For spike {spike_no} a change in temperature sign was observed. This spike will be omitted from analysis')
						continue
					spike_date_time = [date for (date,celsius) in data_list if celsius == spike_temp][0]
					spike_duration = spike_dates_times[-1] - spike_dates_times[0]
					total_spikes_duration += spike_duration
					self._spikes[formatted_date]['individual_spikes'].append({'spike_no': spike_no, 'extreme_spike_temp':spike_temp,'extreme_date_time': spike_date_time, 'spike_duration': spike_duration})
				self._spikes[formatted_date]['total_spikes_duration'] = total_spikes_duration
				self._spikes = {k:dict(v) for k,v in self._spikes.items()} #turn to regular dictionary for easy viewing
				return self._spikes[formatted_date]
			else:
				return None
		return self._spikes[formatted_date]

# def analyze_spikes_(self, date):
# 	spike_dict = self.prepare_spike_dict_from_(date)
# 	if spike_dict:
# 		for spike_no, spike_info in spike_dict[date]['individual_spikes'].items():
# 			if spike_info['single_spike_duration'] > Limits.limits[self._storage_condition]['single_spike_duration']:
# 				print(f'Individual spike of {spike_info['spike_duration']} mins was observed at {spike_info['extreme_date_time']}')
# 			if spike_dict['extreme_spike_temp'] > Limits.limits[self._storage_condition]['high_alert'] or if spike_dict['extreme_spike_temp'] < Limits.limits[self._storage_condition]['low_alert']:
# 				print(f'Individual spike equalling {spike_info['extreme_spike_temp']} Celsius was observed at {spike_info['extreme_date_time']} ')
# 		if spike_dict['total_spikes_duration'] > Limits.limits[self._storage_condition]['total_spike_duration']:
# 			print(f'Total duration of temperature spikes on {date} was {spike_dict['total_spikes_duration']} mins')

# 		if not total_spike_duration_acceptable() or if not single_spike_duration_acceptable() or if not extreme_spike_temperature_acceptable():
# 			self._calculate_daily_MKT_for_(date)
	
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
	def original_data(self):
		return self._original_data
	@property
	def min(self):
		return self._min
	@property
	def max(self):
		return self._max
	@property
	def average(self):
		return self._average
	@property
	def median(self):
		return self._median
	@property
	def data_matrix_size(self):
		return self._data_matrix_size
	@property
	def data_coll_freq(self):
		return self._data_coll_freq
	@property
	def high_alarm(self):
		return self._high_alarm
	@property
	def low_alarm(self):
		return self._low_alarm


class USBLogger():
	def __init__(self, logger_id, serial_no, data, file_basename):
		self._data = TemperatureData(data, owner = self)
		self._id = logger_id
		self._serial_number = serial_no
		self._file_basename = file_basename
		self._storage_condition = self._check_storage_condition()
	
	@classmethod
	def read_from(cls,file_path):
		file_contents = open(file_path)
		file_basename = os.path.basename(file_path)
		header = next(file_contents)
		logger_id, serial_no_idx = obtain_logger_id_from(header)
		serial_no, temperature_data = obtain_serial_numb_temps_from(file_contents, serial_no_idx)
		return cls(logger_id,serial_no,temperature_data, file_basename)
	
	# @classmethod
	# def check_low_high_alarms(cls):
	# 	storage_condition = input(f'Please specify which storage conditions this logger "{self._file_basename}" was used to monitor? Enter either C (cold storage, hplc fridge), or FI (fridge), or FZ (freezer), or 25C (25°C), or 50C (50°C): ')
	# 	return storage_condition
		
	# 	try:
	# 		self._data.add_low_high_alarms(storage_condition)
	# 		self._data._storage_condition = storage_condition
	# 	except KeyError:
	# 		print(f'Storage condition "{storage_condition}" is not in Alarms dictionary. Correct and try again.')
	


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
		storage_condition = input(f'Please specify which storage conditions this logger "{self._file_basename}" was used to monitor? Enter either C (cold storage, hplc fridge), or FI (fridge), or FZ (freezer), or 25C (25°C), or 50C (50°C): ')
		return storage_condition
	
	# def check_low_high_alarms(self):
	# 	storage_condition = input(f'Please specify which storage conditions this logger "{self._file_basename}" was used to monitor? Enter either C (cold storage, hplc fridge), or FI (fridge), or FZ (freezer), or 25C (25°C), or 50C (50°C): ')
	# 	try:
	# 		self._data.add_low_high_alarms(storage_condition)
	# 		self._data._storage_condition = storage_condition
	# 	except KeyError:
	# 		print(f'Storage condition "{storage_condition}" is not in Alarms dictionary. Correct and try again.')
	
	@property
	def data(self):
		return self._data
	@property
	def id(self):
		return self._id
	@property
	def serial_number(self):
		return self._serial_number
	

class XLSXReport():
	def __init__(self, loggers):
		self._loggers = loggers
		self._file_name = self.get_file_name()
		self._wb = Workbook(f'{self._file_name}.xlsx')
		self._ws = self._wb.add_worksheet(self._file_name)
		self._data_location = {}

	@classmethod
	def create_from(cls, loggers):
		if data_collection_frequency_check(loggers):
			return cls(loggers)
		return cls(None)

	def get_file_name(self):
		formatted_today = datetime.now().strftime('%Y-%m-%d')
		return f'{formatted_today}_usb_data_loggers'
	
	def insert_data(self):
		if not self._loggers:
			return None
		start_col = 10 #column count starts at 10 to avoid overlapping data with the chart in A1
		x_axis_location = {'min_col':0, 'min_row':0, 'max_row':0}
		date_format = self._wb.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})

		for usb_logger in self.loggers:
			usb_logger_data = usb_logger.prepare_for_reporting()
			column_names = usb_logger.prepare_column_names(usb_logger.data.data_matrix_size['data_width'])
			row_min, row_max = get_data_start_end(usb_logger_data, column_names)

			if row_max > x_axis_location['max_row']: #select longest data set to be used as x-axis in xlsx report for overlaying all usb loggers 
				x_axis_location['min_row'] = row_min 
				x_axis_location['max_row'] = row_max
				x_axis_location['min_col'] = start_col
			y_axis_location = {'min_col':start_col + 2, 'min_row':row_min, 'max_row':row_max}# select temperature data for y-axis
			
			for row_idx, data_row in enumerate(usb_logger_data):
				for column_idx,data_column in enumerate(data_row):
					if isinstance(data_column, datetime):
						self._ws.write(row_idx, start_col + column_idx, data_column, date_format) #to ensure datetime stamps are written properly in xlsx file
					else:
						self._ws.write(row_idx, start_col + column_idx, data_column)

			start_col = start_col + usb_logger.data.data_matrix_size['data_width'] + 1
			self._data_location[usb_logger] = {'x_axis_location':x_axis_location,'y_axis_location':y_axis_location}
	
	def insert_graph(self):
		if not self._loggers:
			return None
		chart = self._wb.add_chart({'type': 'scatter', 'subtype': 'smooth'})
		chart.set_title({'name': 'Temperature Data'})
		chart.set_x_axis({'name': 'Row','position': 'bottom'})
		chart.set_y_axis({'name': 'Temperature (°C)', 'crossing': 'min'})
		chart.set_legend({'position': 'right'})
	
		for logger, data_location in self._data_location.items():
			x_axis_dict = data_location['x_axis_location']
			y_axis_dict = data_location['y_axis_location']
			chart.add_series({
                    'name': logger.id,
                    'categories': [self.file_name, 
                                x_axis_dict['min_row'], 
                                x_axis_dict['min_col'],
                                x_axis_dict['max_row'], 
                                x_axis_dict['min_col']],
                    'values': [self.file_name,
                            y_axis_dict['min_row'], 
                            y_axis_dict['min_col'],
                            y_axis_dict['max_row'], 
                            y_axis_dict['min_col']],
                })
		self._ws.insert_chart('A1', chart)
		self._wb.close()

	@property
	def loggers(self):
		return self._loggers
	@property
	def file_name(self):
		return self._file_name
	@property
	def wb(self):
		return self._wb
	@property
	def data_frequency_check(self):
		return self.data_frequency_check()

class Limits():
	limits = {'C': {'low_alarm': -10.0, 'high_alarm': 10.0, 'low_alert': -20.0, 'high_alert':-20.0, 'single_spike_duration':3600, 'total_spike_duration': 10800},
		   	'FI': {'low_alarm': 2.0, 'high_alarm': 8.0,'low_alert': 0.0, 'high_alert': 15.0, 'single_spike_duration':3600, 'total_spike_duration':10800},
			'FZ': {'low_alarm': -25.0, 'high_alarm': -15.0,'low_alert': -30.0, 'high_alert': -0.1, 'single_spike_duration':3600, 'total_spike_duration':10800},
			'25C': {'low_alarm': 24.0, 'high_alarm': 26.0,'low_alert': 15.0, 'high_alert': 30.0, 'single_spike_duration':900, 'total_spike_duration':10800},
			'50C': {'low_alarm': 45.0, 'high_alarm': 55.0,'low_alert': 25.0, 'high_alert': 60.0, 'single_spike_duration':900, 'total_spike_duration':10800}
	}
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

def obtain_serial_numb_temps_from(file_contents, serial_no_idx):
	temperature_data = []
	serial_no = None
	for line in file_contents:
		split_line = line.split(",")
		if not serial_no:
			serial_no = split_line[serial_no_idx].strip()
		row_data = {
            'row_number': int(split_line[0].strip()),
            'date_time': datetime.strptime(split_line[1].strip(), "%Y-%m-%d %H:%M:%S"),
            'celsius': float(split_line[2].strip())
        }
		if len(split_line) > 3:
			if serial_no == split_line[3].strip():
				pass
			else:
				row_data['high_alarm'] = float(split_line[3].strip()) if split_line[3].strip() else None
			if len(split_line) > 4:
				row_data['low_alarm'] = float(split_line[4].strip()) if split_line[4].strip() else None

		temperature_data.append(row_data)
	return serial_no, temperature_data


def obtain_logger_id_from(header):
	split_header = [field.strip() for field in header.split(',')]
	id = split_header[0].strip()
	serial_no_idx = split_header.index('Serial Number') #position of Serial Number column varies
	return id, serial_no_idx


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

	
if __name__ == '__main__':	
	# file_list = [FILE_1,FILE_2,FILE_3,FILE_5,FILE_6,FILE_7,FILE_8]
	SPIKE_FILE = r'C:\Users\User\Desktop\Misc\usb_logger_parser\ACP169_30-03-2020_artificial_spikes.txt'
	file_list = [SPIKE_FILE]
	usb_loggers = [USBLogger.read_from(file) for file in file_list]
	for logger in usb_loggers:
		# logger.check_low_high_alarms()
		# logger.data.prepare_spike_dict_()
		# print(logger.data._spikes)
		mkt = logger.data._calculate_daily_MKT_for_(date(2020, 3, 16))
		print(mkt)

	# report = XLSXReport.create_from(usb_loggers)
	# report.insert_data()
	# report.insert_graph(