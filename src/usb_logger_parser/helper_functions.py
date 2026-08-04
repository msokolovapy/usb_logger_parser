import pandas as pd
import os
import sys
import logging
from collections import Counter
from importlib.resources import files

logger = logging.getLogger(__name__)


def read(traversable_object):
    """Reads a CSV file from an importlib.resources Traversable object and returns pandas DataFrame together with some metadata"""
    with traversable_object.open("rb") as file:
        valid_df = validate_and_convert(file)
    df_temp_data, logger_id, serial_numb = parse_(valid_df)
    file_basename = traversable_object.name
    return df_temp_data, logger_id, serial_numb, file_basename


def get_average_temp(df):
    return df["celsius"].mean()


def parse_(df):
    df = df.copy()
    df.rename(
        columns={
            "Time": "date_time",
            "Celsius": "celsius",
            "High Alarm": "high_alarm",
            "Low Alarm": "low_alarm",
            "Serial Number": "serial_number",
        },
        inplace=True,
    )
    logger_id = df.columns.values[0]
    serial_numb = df["serial_number"][0]
    df = df.rename(columns={logger_id: "row_numb"})
    df.drop(columns=["serial_number"], inplace=True)
    return df, logger_id, serial_numb


def get_user_confirmation(file_basename, logger_id):
    user_input = input(
        f"It looks like your temperature trace '{file_basename}' for logger {logger_id} may have come from either cold storage or fridge.Please confirm here (FG/CS):"
    )
    return user_input


def validate_and_convert(file):
    try:
        df = pd.read_csv(file, encoding="latin-1")
        if df.empty:
            logger.warning(f"Empty dataframe when trying to load {file}")
            raise ValueError(f"Empty dataframe when trying to load {file}")

        required_columns = ["Time", "Celsius"]
        missing_columns = missing_column_check(df.columns, required_columns)
        if missing_columns:
            logger.warning(f"Some columns are missing: {(', ').join(missing_columns)}")
            raise KeyError(f"Some columns are missing: {(', ').join(missing_columns)}")

        df.columns = df.columns.map(read_convert_headers)

        for column in required_columns:
            if df[column].isna().any():
                logger.warning(f"Some values are missing in '{column}' column")
                raise ValueError(f"Some values are missing in '{column}' column")

        df = convert_dtypes(df)

        return df
    except (ValueError, KeyError) as e:
        raise e from None  # re-raising independently so that either error is not caught by 'except Exception as e'
    except Exception as e:
        logger.error(f"Unexpected error ({e}) occured when trying to load '{file}'")
        raise e from None


def get_spike_duration(pandas_series_date_time):
    spike_duration = int(
        (pandas_series_date_time.max() - pandas_series_date_time.min()).total_seconds()
        / 60
    )
    return spike_duration


def get_extreme_date_time(pandas_series_date_time, df):
    filtered = df.loc[pandas_series_date_time.index, "celsius"]
    mask = filtered.abs().idxmax()
    extreme_date_times = pandas_series_date_time.loc[mask]
    return extreme_date_times


def get_extreme_temp(pandas_series_celsius):
    mask = pandas_series_celsius.abs().idxmax()
    return pandas_series_celsius.loc[mask]


def convert_timestamps(df):
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col]).dt.to_pydatetime()
        if col == "spike_date":
            df[col] = pd.to_datetime(df[col]).dt.date
    return df


def data_collection_frequency_check(storage_units):
    if len(storage_units) == 1:
        return True  # test always passes for one storage unit as there is nothing to compare this one storage unit to
    freq_counter = Counter(unit.logger.ave_data_coll_freq for unit in storage_units)
    most_common_value = freq_counter.most_common()[0][0]
    for unit in storage_units:
        if unit.logger.ave_data_coll_freq != most_common_value:
            logger.warning(
                f"Data frequency collection for logger {unit.logger.id} differs from the rest of the temperature data collected. To ensure meaningful comparison, remove logger {unit.logger.id} and try again"
            )
            raise ValueError(
                f"Data frequency collection for logger {unit.logger.id} differs from the rest of the temperature data collected. To ensure meaningful comparison, remove logger {unit.logger.id} and try again"
            )
    return True


def get_ave_data_coll_freq(df):
    data_coll_freq_series = df["date_time"].diff()
    ave_data_coll_freq = round(data_coll_freq_series.mean().total_seconds() / 60, 6)
    return ave_data_coll_freq


def insert_metadata_header(data, metadata_list):
    for metadata in metadata_list:
        data.insert(0, metadata)
    return data


def extract_to_list(df):
    df = convert_timestamps(df)
    values = df.values.tolist()
    column_names = df.columns.tolist()
    values.insert(
        0, column_names
    )  # to obtain data as a list of lists for easy writing to xlsx workbook later
    return values


def get_files(package, folder):
    found_files = []
    try:
        resource_dir = files(package).joinpath(folder)
        for entry in resource_dir.iterdir():
            if entry.is_file():
                found_files.append(entry)
        if len(found_files) == 0:
            logger.warning(
                f'No raw temperature data files found in "{folder}" directory'
            )
            raise ValueError(
                f'No raw temperature data files found in "{folder}" directory'
            )
    except ValueError:
        raise
    except Exception:
        logger.error(f"Unexpected error when trying to access {package}.{folder}")
        raise ValueError(f"Unexpected error when trying to access {package}.{folder}")
    return found_files


def missing_column_check(columns, required_cols):
    """Check whether required columns ('time', 'celsius') are present among the given column names
    while avoiding direct comparison of strings to each other due to mangled encoding around the degree symbol.
    """
    missing_cols = []
    try:
        required_cols_lower = [req_col.lower() for req_col in required_cols]
        columns_lower = [col.lower() for col in columns]
    except AttributeError:
        logger.warning("Failed to convert column names to lower-case")
        raise AttributeError("Failed to convert column names to lower-case")
    except Exception:
        logger.warning(
            "Unknown error when trying to convert column names to lower-case"
        )
        raise AttributeError(
            "Unknown error when trying to convert column names to lower-case"
        )
    for req in required_cols_lower:
        if req not in "".join(
            columns_lower
        ):  # create mega-string of all column names to quickly check if required column is present
            missing_cols.append(req.capitalize())
    return missing_cols


def read_convert_headers(header):
    expected_headers = ["Time", "Celsius", "High Alarm", "Low Alarm", "Serial Number"]
    for hd in expected_headers:
        try:
            if hd.lower() in header.lower():
                return hd
        except AttributeError:
            logger.warning(f"Failed to convert header '{header}' to an expected header")
            raise AttributeError(
                f"Failed to convert header '{header}' to an expected header"
            )
        except Exception:
            logger.warning("Unexpected error occured when trying to convert header")
            raise Exception("Unexpected error occured when trying to convert header")
    return header


def convert_dtypes(df):
    expected = {
        "Serial Number": str,
        "Celsius": float,
        "High Alarm": float,
        "Low Alarm": float,
        "Time": pd.to_datetime,
    }
    for col, conversion_type in expected.items():
        if col in df.columns:
            try:
                if conversion_type is pd.to_datetime:
                    df[col] = conversion_type(df[col])
                else:
                    df[col] = df[col].astype(conversion_type)
            except ValueError:
                logger.warning(
                    f"Failed to convert column '{col}' using {conversion_type}"
                )
                raise ValueError(
                    f"Failed to convert column '{col}' using {conversion_type}"
                )
    return df
