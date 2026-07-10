import unittest

from src.usb_logger_parser.storage_units import StorageCondition, Freezer
from src.usb_logger_parser.analytical_service import AnalyticalService
from src.usb_logger_parser.reporting_service import (
    ReportingService,
)


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


class TestReportRawData(unittest.TestCase):
    def test_report_raw_data(self):
        reporting_service = ReportingService()
        file_list = [
            r"/workspaces/usb_logger_parser/ACP169_30-03-2020_artificial_spikes.txt"
        ]
        storage_units = [StorageCondition.create_from_(file) for file in file_list]

        reporting_service.report_raw_data(storage_units)


class TestReportSpikes(unittest.TestCase):
    def test_report_spikes(self):
        analytical_service = AnalyticalService()
        reporting_service = ReportingService()
        file_list = [
            r"/workspaces/usb_logger_parser/ACP169_30-03-2020_artificial_spikes.txt"
        ]
        storage_conditions = [StorageCondition.create_from_(file) for file in file_list]
        temp_spikes = analytical_service.analyze_spikes(storage_conditions)
        reporting_service.report_spikes(temp_spikes)


if __name__ == "__main__":
    unittest.main()
