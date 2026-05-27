from xlsxwriter import Workbook
import logging
from datetime import datetime
from src.usb_logger_parser.helper_functions import data_collection_frequency_check

logger = logging.getLogger(__name__)


class ReportingService:
    def __init__(self):
        self.data_to_graph = []

    def report_spike_dict_(self, spike_dicts):
        return XlSXSummary(spike_dict)

    def report_data_(self, storage_units):
        for unit in storage_units:
            if not data_collection_frequency_check(storage_units):
                logger.warning(
                    "Mismatch of USB data loggers' data collection frequencies"
                )
                raise ValueError(
                    "Mismatch of USB data loggers' data collection frequencies"
                )
            prepared_data = self.update_axes_range(unit)
            self.data_to_graph.append(prepared_data)
        return XLSXGraph(self.data_to_graph)

    def update_axes_range(unit):
        data_row_min, data_row_max, prepared_temp_data, data_width = (
            parse_for_reporting_(unit)
        )
        xy_axes_bounds = XYAxesBounds()

        if data_row_max > xy_axes_bounds.x_row_max:
            xy_axes_bounds.x_row_min = row_min
            xy_axes_bounds.x_row_max = row_max
            xy_axes_bounds.x_col_min = start_col

        xy_axes_bounds.y_col_min = self.start_col + 2
        xy_axes_bounds.y_row_min = row_min
        xy_axes_bounds.y_row_max = row_max

        return {
            unit: {
                "data": prepared_temp_data,
                "xy_axes_bounds": xy_axes_bounds,
                "data_width": data_width,
            }
        }


class XLSXSummary:
    def __init__(self, spike_dict):
        self.spike_dict = spike_dict
        self.file_name = self.get_file_name()
        self.wb = Workbook(f"{self.file_name}.xlsx")
        self.ws = self.wb.add_worksheet(self.file_name)

    def get_file_name(self):
        formatted_today = datetime.now().strftime("%Y-%m-%d")
        return f"{formatted_today}_spikes_summary"

    def insert_data(spike_dict):
        pass


class XLSXGraph:
    def __init__(self, data_to_graph):
        self.data_to_graph = data_to_graph
        self.start_col = 10
        self.file_name = self.get_file_name()
        self.wb = Workbook(f"{self._file_name}.xlsx")
        self.ws = (
            self.wb.add_workbook()
        )  # keeping worksheet as attribute as xlsxwriter cannot re-open worksheets

    def get_file_name(self):
        formatted_today = datetime.now().strftime("%Y-%m-%d")
        return f"{formatted_today}_usb_data_loggers_graph"

    def insert_data(self):
        if not self.data_to_graph:
            logger.warning(f"No data for visualisation was provided")
            raise ValueError(f"No data for visualisation was provided")

        for data in self.data_to_graph:
            temp_data = data[unit]["data"]
            data_width = data[unit]["data_width"]

            for row_idx, data_row in enumerate(temp_data):
                for column_idx, data_column in enumerate(data_row):
                    if isinstance(data_column, datetime):
                        date_format = self.wb.add_format(
                            {"num_format": "yyyy-mm-dd hh:mm:ss"}
                        )
                        self.ws.write(
                            row_idx,
                            self.start_col + column_idx,
                            data_column,
                            date_format,
                        )  # to ensure datetime stamps are written properly in xlsx file
                    else:
                        self.ws.write(row_idx, self.start_col + column_idx, data_column)

            self.start_col = self.start_col + data_width + 1

    def insert_graph(self):
        chart = self.wb.add_chart({"type": "scatter", "subtype": "smooth"})
        chart.set_title({"name": "Temperature Data"})
        chart.set_x_axis({"name": "Row", "position": "bottom"})
        chart.set_y_axis({"name": "Temperature (°C)", "crossing": "min"})
        chart.set_legend({"position": "right"})

        for unit, data in self.data_to_graph.items():
            xy_axes_bounds = data["xy_axes_bounds"]
            chart.add_series(
                {
                    "name": unit.logger.id,
                    "categories": [
                        self.file_name,
                        xy_axes_bounds.x_row_min,
                        xy_axes_bounds.x_col_min,
                        xy_axes_bounds.x_row_max,
                        xy_axes_bounds.x_col_min,
                    ],
                    "values": [
                        self.file_name,
                        xy_axes_bounds.y_row_min,
                        xy_axes_bounds.y_col_min,
                        xy_axes_bounds.y_row_max,
                        xy_axes_bounds.y_col_min,
                    ],
                }
            )
        self.ws.insert_chart("A1", chart)
        self.wb.close()


class XYAxesBounds:
    def __init__(self):
        self.x_axis_bounds = {"col_min": 0, "col_max": 0, "row_min": 0, "row_max": 0}
        self.y_axis_bounds = {"col_min": 0, "col_max": 0, "row_min": 0, "row_max": 0}

    @property
    def y_row_min(self):
        return self.y_axis_bounds["row_min"]

    @property
    def y_row_max(self):
        return self.y_axis_bounds["row_max"]

    @property
    def y_col_min(self):
        return self.y_axis_bounds["col_min"]

    @property
    def y_col_max(self):
        return self.y_axis_bounds["col_max"]

    @property
    def x_row_min(self):
        return self.x_axis_bounds["row_min"]

    @property
    def x_row_max(self):
        return self.x_axis_bounds["row_max"]

    @property
    def x_col_min(self):
        return self.x_axis_bounds["col_min"]

    @property
    def x_col_max(self):
        return self.x_axis_bounds["col_max"]


# OLD Stuff here:

# from xlsxwriter import Workbook
# import logging
# from datetime import datetime
# from src.usb_logger_parser.helper_functions import data_collection_frequency_check

# logger = logging.getLogger(__name__)


# class ReportingService:
#     def __init__(self):
#         pass

#     def report_spike_dict_(self, spike_dicts):
#         return XlSXSummary(spike_dict)

#     def report_data_(self, storage_units):
#         if data_collection_frequency_check(storage_units):
#             return XLSXGraph(storage_units)
#         logger.warning("Mismatch of USB data loggers's data collection frequencies")
#         raise ValueError("Mismatch of USB data loggers's data collection frequencies")


# class XLSXSummary:
#     def __init__(self, spike_dict):
#         self.spike_dict = spike_dict
#         self.file_name = self.get_file_name()
#         self.wb = Workbook(f"{self.file_name}.xlsx")
#         self.ws = self.wb.add_worksheet(self.file_name)

#     def get_file_name(self):
#         formatted_today = datetime.now().strftime("%Y-%m-%d")
#         return f"{formatted_today}_spikes_summary"

#     def insert_data(spike_dict):
#         pass


# class XLSXGraph:
#     def __init__(self, df):
#         self.loggers = loggers
#         self.file_name = self.get_file_name()
#         self.wb = Workbook(f"{self._file_name}.xlsx")
#         self.ws = self._wb.add_worksheet(self._file_name)
#         self.data_location = {}

#     @classmethod
#     def create_for_(cls, loggers):
#         if data_collection_frequency_check(loggers):
#             return cls(loggers)
#         return cls(None)

#     def get_file_name(self):
#         formatted_today = datetime.now().strftime("%Y-%m-%d")
#         return f"{formatted_today}_usb_data_loggers_graph"

#     def insert_data(self):
#         if not self._loggers:
#             return None
#         start_col = 10  # column count starts at 10 to avoid overlapping data with the chart in A1
#         x_axis_location = {"min_col": 0, "min_row": 0, "max_row": 0}
#         date_format = self._wb.add_format({"num_format": "yyyy-mm-dd hh:mm:ss"})

#         for usb_logger in self.loggers:
#             usb_logger_data = usb_logger.prepare_for_reporting()
#             column_names = usb_logger.prepare_column_names(
#                 usb_logger.data.data_matrix_size["data_width"]
#             )
#             row_min, row_max = get_data_start_end(usb_logger_data, column_names)

#             if (
#                 row_max > x_axis_location["max_row"]
#             ):  # select longest data set to be used as x-axis in xlsx report for overlaying all usb loggers
#                 x_axis_location["min_row"] = row_min
#                 x_axis_location["max_row"] = row_max
#                 x_axis_location["min_col"] = start_col
#             y_axis_location = {
#                 "min_col": start_col + 2,
#                 "min_row": row_min,
#                 "max_row": row_max,
#             }  # select temperature data for y-axis

#             for row_idx, data_row in enumerate(usb_logger_data):
#                 for column_idx, data_column in enumerate(data_row):
#                     if isinstance(data_column, datetime):
#                         self._ws.write(
#                             row_idx, start_col + column_idx, data_column, date_format
#                         )  # to ensure datetime stamps are written properly in xlsx file
#                     else:
#                         self._ws.write(row_idx, start_col + column_idx, data_column)

#             start_col = start_col + usb_logger.data.data_matrix_size["data_width"] + 1
#             self._data_location[usb_logger] = {
#                 "x_axis_location": x_axis_location,
#                 "y_axis_location": y_axis_location,
#             }

#     def insert_graph(self):
#         if not self._loggers:
#             return None
#         chart = self._wb.add_chart({"type": "scatter", "subtype": "smooth"})
#         chart.set_title({"name": "Temperature Data"})
#         chart.set_x_axis({"name": "Row", "position": "bottom"})
#         chart.set_y_axis({"name": "Temperature (°C)", "crossing": "min"})
#         chart.set_legend({"position": "right"})

#         for logger, data_location in self._data_location.items():
#             x_axis_dict = data_location["x_axis_location"]
#             y_axis_dict = data_location["y_axis_location"]
#             chart.add_series(
#                 {
#                     "name": logger.id,
#                     "categories": [
#                         self.file_name,
#                         x_axis_dict["min_row"],
#                         x_axis_dict["min_col"],
#                         x_axis_dict["max_row"],
#                         x_axis_dict["min_col"],
#                     ],
#                     "values": [
#                         self.file_name,
#                         y_axis_dict["min_row"],
#                         y_axis_dict["min_col"],
#                         y_axis_dict["max_row"],
#                         y_axis_dict["min_col"],
#                     ],
#                 }
#             )
#         self._ws.insert_chart("A1", chart)
#         self._wb.close()

#     @property
#     def loggers(self):
#         return self._loggers

#     @property
#     def file_name(self):
#         return self._file_name

#     @property
#     def wb(self):
#         return self._wb

#     @property
#     def data_frequency_check(self):
#         return self.data_frequency_check()
