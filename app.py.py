import os
from statistics import mean, median
from datetime import datetime
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
	"""This class stores temperature data obtained via Lascar USB data logger.
	Instances of this class can be compared to each other using '==' operator"""
	def __init__(self, temperature_data):
		self._original_data = temperature_data #list of (row_number, date_time_stamp, degrees_celsius) tuples
		self._max = self.select_max_temperature()
		self._min = self.select_min_temperature()
		self._average = self.select_average_temperature()
		self._median = self.select_median_temperature()
		self._data_coll_freq = self.determine_ave_data_coll_frequency()
		self._data_matrix_size = {'data_width':len(self._original_data[0]),	'data_lenth':len(self._original_data)}

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


class USBLogger():
	def __init__(self, logger_id, serial_no, data):
		self._data = TemperatureData(data)
		self._id = logger_id
		self._serial_number = serial_no
	
	@classmethod
	def read_from(cls,file_path):
		file_contents = open(file_path)
		header = next(file_contents)
		logger_id, serial_no_idx = obtain_logger_id_from(header)
		serial_no, temperature_data = obtain_serial_numb_temps_from(file_contents, serial_no_idx)
		return cls(logger_id,serial_no,temperature_data)

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
			return cls(loggers = loggers)
		return cls(loggers = [])

		
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
			y_axis_location = {'min_col':start_col + 2, 'min_row':row_min, 'max_row':row_max}# select data for y-axis
			
			for row_idx, data_row in enumerate(usb_logger_data):
				for column_idx,data_column in enumerate(data_row):
					if isinstance(data_column, datetime):
						self._ws.write(row_idx, start_col + column_idx, data_column, date_format)
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

	# def insert_graph(self):
	# 	if not self._loggers:
	# 		return None
	# 	ws = self.wb[f'{self.file_name}']
	# 	chart = ScatterChart()
	# 	chart.title = "Temperature Data"
	# 	chart.x_axis.title = "Row"
	# 	chart.y_axis.title = "Temperature (°C)"
	# 	chart.x_axis.delete = False
	# 	chart.y_axis.delete = False
	# 	chart.legend.overlay = False
		
		
	# 	for logger,data_location in self._data_location.items():
	# 		x_axis_dict = data_location['x_axis_location']
	# 		y_axis_dict = data_location['y_axis_location']
	# 		x_values = Reference(ws, min_col=x_axis_dict['min_col'], min_row=x_axis_dict['min_row'], max_row=x_axis_dict['max_row'])
	# 		y_values = Reference(ws, min_col=y_axis_dict['min_col'], min_row=y_axis_dict['min_row'], max_row=y_axis_dict['max_row'])
	# 		series = Series(y_values, x_values, title = logger.id)
	# 		chart.series.append(series)
	# 	ws.add_chart(chart, "A1")
	# 	file_path_save = rf'C:\Users\User\Desktop\Misc\{self._file_name}.xlsx'
	# 	self.wb.save(file_path_save)
	# 	os.startfile(file_path_save)

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
	#uses column names to extract starting and ending data row indices and adjusts them for openpyxl. Data starts immediately after column names
	row_min = logger_data.index(column_names) + 2
	row_max = len(logger_data)
	return row_min, row_max

	
if __name__ == '__main__':	
	file_list = [FILE_1,FILE_2,FILE_3,FILE_4, FILE_5,FILE_6,FILE_7,FILE_8]
	usb_loggers = [USBLogger.read_from(file) for file in file_list]
	report = XLSXReport.create_from(usb_loggers)
	report.insert_data()
	report.insert_graph()