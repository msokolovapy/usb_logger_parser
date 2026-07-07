import unittest

from src.usb_logger_parser.storage_units import StorageCondition, Freezer
from src.usb_logger_parser.analytical_service import AnalyticalService
from src.usb_logger_parser.reporting_service import (
    ReportingService,
)


class TestReportRawData(unittest.TestCase):
    def test_report_raw_data(self):
        today = datetime.now()strftime("%Y-%m-%d")
        test_cases = [
            {
                "file_source": r"/workspaces/usb_logger_parser/ACP169_30-03-2020_artificial_spikes.txt",
                "x_axis": 10,
                "y_axis": 12,
                "row_start": 4,
                "row_end": 1000,
            }
        ]
        file_destination = r"/workspaces/usb_logger_parser/" + f'{today}_usb_logger_graph.xlsx'
        reporting_service = ReportingService()
        file_list = [case["file_source"] for case in test_cases]
        storage_units = [StorageCondition.create_from_(file) for file in file_list]

        reporting_service.report_raw_data(storage_units)
        wb = openpyxl.load_workbook(file_destination)


class TestColdStorageUnit(unittest.TestCase):
    def test_cold_storage_unit_type(self):
        file_list = [
            r"/workspaces/usb_logger_parser/ACP169_30-03-2020_artificial_spikes.txt"
        ]
        storage_units = [StorageCondition.create_from_(file) for file in file_list]
        expected_values = [
            {
                "file_name": "ACP169_30-03-2020_artificial_spikes.txt",
                "unit_type": Freezer,
            }
        ]
        for unit in storage_units:
            with self.subTest(f"testing {unit.logger.id} unit type"):
                for expected in expected_values:
                    if unit.metadata == expected["file_name"]:
                        self.assertIsInstance(unit, expected["unit_type"])
