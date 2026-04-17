from app import logger
import pandas as pd
import os
import sys


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


def validate_(file):
	try:
		df = pd.read_csv(file, encoding='latin-1')
		if df.empty:
			logger.warning(f"Empty dataframe when trying to load {file}")
			sys.exit(1)

		required_columns = ["Time", "Celsius(°C)"]
		missing_columns = set(required_columns) - set(df.columns)
		if missing_columns:
			logger.warning(f"Some columns are missing: {missing_columns}")
			sys.exit(1)

		for column in required_columns:
			if df[column].isna().any():
				logger.warning(f"Some values are missing in '{column}' column")
				sys.exit(1)
		return file

	except FileNotFoundError:
		logger.error(f"No file '{file}' found")
	except Exception as e:
		logger.exception(f"Unexpected error ({e}) occured when trying to load {file}")
	sys.exit(1)