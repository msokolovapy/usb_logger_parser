from xlsxwriter import Workbook

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