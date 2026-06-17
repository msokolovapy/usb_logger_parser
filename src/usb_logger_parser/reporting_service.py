from xlsxwriter import Workbook
import logging
import pandas as pd
from datetime import datetime, date
from src.usb_logger_parser.helper_functions import data_collection_frequency_check

logger = logging.getLogger(__name__)


class ReportingService:
    def __init__(self):
        self.data_to_graph = []

    def prepare_data_for_reporting(self, unit):
        data = extract_to_dict(unit.temp_data)
        data_width = unit.temp_data.shape[1]

        data_with_header = insert_metadata_header(data, unit.metadata)
        data_row_min = (
            len(unit.metadata) + 2
        )  # to account for column fields already present in data
        data_row_max = len(data_with_header)
        return {
            unit: {
                "data": data_with_header,
                "data_row_min": data_row_min,
                "data_row_max": data_row_max,
                "data_width": data_width,
            }
        }

    def report_spikes(self, spike_info_list):
        return XlSXSummary(spike_info_list)

    def report_raw_data(self, storage_units):
        for unit in storage_units:
            if not data_collection_frequency_check(storage_units):
                logger.warning(
                    "Mismatch of USB data loggers' data collection frequencies"
                )
                raise ValueError(
                    "Mismatch of USB data loggers' data collection frequencies"
                )
            prepared_data = self.prepare_data_for_reporting(unit)
            self.data_to_graph.append(prepared_data)
        xlsxgraph = XLSXGraph(self.data_to_graph)
        xlsxgraph.insert_data()
        xlsxgraph.insert_chart()

    # def extract_to_dict(self, df):
    #     data_width = df.shape[1]
    #     df["date_time"] = pd.to_datetime(df["date_time"]).dt.to_pydatetime()
    #     values = df.values.tolist()
    #     column_names = df.columns.tolist() # to obtain data as a list of lists for easy writing to xlsx workbook later
    #     values.insert(0, column_names)
    #     values = tuple([tuple(value) for value in values]) #to make tuple of tuples for immutability
    #     return values, data_width

    # def insert_metadata_header_(self, data, data_width, logger_metadata):
    #     data_row_min = 1  # row 0 is already taken by column names
    #     for metadata in logger_metadata:
    #         metadata_header = [metadata, *[None] * (data_width - 1)]
    #         data.insert(0, metadata_header)
    #         data_row_min += 1
    #     data_row_max = len(data)
    #     return data_row_min, data_row_max, data

    # def prepare_data_for_reporting_(self, unit):
    #     data, data_width = self.extract_to_dict(unit.temp_data)
    #     metadata = (unit.logger.id, unit.logger.serial_numb)
    #     data_row_min, data_row_max, data_with_header = self.insert_metadata_header_(
    #         data, data_width, metadata
    #     )
    #     return {
    #         unit: {
    #             "data": data_with_header,
    #             "data_row_min": data_row_min,
    #             "data_row_max": data_row_max,
    #             "data_width": data_width,
    #         }
    #     }


class XLSXSummary:
    def __init__(self, spikes_list):
        self.spikes_list = spikes_list
        self.file_name = self.get_file_name()
        self.wb = Workbook(f"{self.file_name}.xlsx")
        self.ws = self.wb.add_worksheet(
            self.file_name
        )  # keeping worksheet as attribute as xlsxwriter cannot re-open worksheets
        self.datetime_format = self.wb.add_format(
            {"num_format": "dd/mm/yyyy hh:mm:ss"}
        )  # essential for xlxswriter to save dates as native Excel format
        self.date_format = self.wb.add_format(
            {"num_format": "dd/mm/yyyy"}
        )  # same as above

    def get_file_name(self):
        formatted_today = datetime.now().strftime("%Y-%m-%d")
        return f"{formatted_today}_spikes_summary"

    def insert_data(self):
        current_row = 0
        for spike_tuple in self.spikes_list:
            for spike_details in spike_tuple:
                for col_idx, value in enumerate(spike_details):
                    if isinstance(value, datetime):
                        self.ws.write(current_row, col_idx, value, self.datetime_format)
                    elif isinstance(value, date):
                        self.ws.write(current_row, col_idx, value, self.date_format)
                    else:
                        self.ws.write(current_row, col_idx, value)
                current_row += 1
            self.ws.write_row(
                current_row, 0, (None,) * 1
            )  # for ease of reading - insert blank row between spike info from different usb loggers
            current_row += 1
        self.wb.close()


class XLSXGraph:
    def __init__(self, data_to_graph):
        self.data_to_graph = data_to_graph
        self.start_col = 10
        self.x_axis_bounds = {
            "col_min": 0,
            "col_max": 0,
            "row_min": 0,
            "row_max": 0,
        }
        self.file_name = self.get_file_name()
        self.wb = Workbook(f"{self.file_name}.xlsx")
        self.ws = self.wb.add_worksheet(
            f"{self.file_name}"
        )  # keeping worksheet as attribute as xlsxwriter cannot re-open worksheets
        self.datetime_format = self.wb.add_format(
            {"num_format": "dd/mm/yyyy hh:mm:ss"}
        )  # essential for xlxswriter to save dates as native Excel format

    def get_file_name(self):
        formatted_today = datetime.now().strftime("%Y-%m-%d")
        return f"{formatted_today}_usb_loggers_graph"

    def insert_data(self):
        if not self.data_to_graph:
            logger.warning(f"No data for visualisation was provided")
            raise ValueError(f"No data for visualisation was provided")

        for data in self.data_to_graph:
            for unit, prepared_data in data.items():
                temp_data = prepared_data["data"]
                data_width = prepared_data["data_width"]
                data_row_min = prepared_data["data_row_min"]
                data_row_max = prepared_data["data_row_max"]

                y_axis_bounds = {
                    "col_min": self.start_col + 2,
                    "col_max": self.start_col + 2,
                    "row_min": data_row_min,
                    "row_max": data_row_max,
                }

                if (
                    data_row_max > self.x_axis_bounds["row_max"]
                ):  # longest x-axis is selected for saving and then overlaying in the chart
                    self.x_axis_bounds["row_max"] = data_row_max
                    self.x_axis_bounds["row_min"] = data_row_min
                    self.x_axis_bounds["col_min"] = self.start_col
                    self.x_axis_bounds["col_max"] = self.start_col

                for row_idx, data_row in enumerate(temp_data):
                    for column_idx, data_column in enumerate(data_row):
                        if isinstance(data_column, datetime):
                            self.ws.write(
                                row_idx,
                                self.start_col + column_idx,
                                data_column,
                                self.datetime_format,
                            )
                        self.ws.write(row_idx, self.start_col + column_idx, data_column)

                self.start_col = self.start_col + data_width + 1
                data[unit]["y_axis_bounds"] = y_axis_bounds

    def insert_chart(self):
        chart = self.wb.add_chart({"type": "scatter", "subtype": "smooth"})
        chart.set_title({"name": "Temperature Data"})
        chart.set_x_axis({"name": "Row Number", "position": "bottom"})
        chart.set_y_axis({"name": "Temperature (°C)", "crossing": "min"})
        chart.set_legend({"position": "right"})

        for data in self.data_to_graph:
            for unit, data in data.items():
                y_axis_bounds = data["y_axis_bounds"]
                chart.add_series(
                    {
                        "name": unit.logger.id,
                        "categories": [
                            self.file_name,
                            self.x_axis_bounds["row_min"],
                            self.x_axis_bounds["col_min"],
                            self.x_axis_bounds["row_max"],
                            self.x_axis_bounds["col_max"],
                        ],
                        "values": [
                            self.file_name,
                            y_axis_bounds["row_min"],
                            y_axis_bounds["col_min"],
                            y_axis_bounds["row_max"],
                            y_axis_bounds["col_max"],
                        ],
                    }
                )
        self.ws.insert_chart("A1", chart)
        self.wb.close()
