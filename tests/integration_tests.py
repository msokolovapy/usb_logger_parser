import unittest
from datetime import datetime
from unittest.mock import patch

from usb_logger_parser.analytical_service import AnalyticalService
from usb_logger_parser.helper_functions import get_files
from usb_logger_parser.reporting_service import (
    ReportingService,
)
from usb_logger_parser.storage_units import Freezer, Fridge, StorageCondition


class TestColdStorageUnit(unittest.TestCase):
    def test_cold_storage_unit_type(self):
        with patch("builtins.input") as mock_input:
            mock_input.return_value = "fg"
            file_list = get_files("usb_logger_parser", "resources")
            storage_units = [StorageCondition.create_from_(file) for file in file_list]
        expected_values = [
            {
                "file_name": "ACP169_30-03-2020_artificial_spikes.txt",
                "unit_type": Freezer,
            },
            {
                "file_name": "ACPL211 in ACPL229 20.5.22 to 3.8.22.txt",
                "unit_type": Fridge,
            },
        ]
        file_basenames = [expected["file_name"] for expected in expected_values]
        for unit in storage_units:
            with self.subTest(f"testing {unit.logger.id} unit type"):
                if unit.file_basename not in file_basenames:
                    self.fail(f"Add logger data {unit.logger.id} to expected_values")
                for expected in expected_values:
                    if unit.file_basename == expected["file_name"]:
                        self.assertIsInstance(unit, expected["unit_type"])


class TestReportRawData(unittest.TestCase):
    def test_report_raw_data(self):
        today = datetime.now().strftime("%Y-%m-%d")
        file_list = get_files("usb_logger_parser", "resources")
        reporting_service = ReportingService(f"{today}_integration_tests_graph")
        with (
            patch(
                "usb_logger_parser.reporting_service.data_collection_frequency_check"
            ) as mock_freq_check,
            patch("builtins.input") as mock_user_input,
        ):
            mock_freq_check.return_value = (
                True  # bypassing data collection frequency check for testing purposes
            )
            mock_user_input.return_value = "fg"  # bypassing mandatory user input for Fridge or ColdStorage object creation
            storage_units = [StorageCondition.create_from_(file) for file in file_list]
            reporting_service.report_raw_data(storage_units)
            mock_freq_check.assert_called()


class TestReportSpikes(unittest.TestCase):
    def test_report_spikes(self):
        today = datetime.now().strftime("%Y-%m-%d")
        analytical_service = AnalyticalService()
        reporting_service = ReportingService(
            f"{today}_integration_tests_spikes_summary"
        )
        file_list = get_files("usb_logger_parser", "resources")
        with patch("builtins.input") as mock_input:
            mock_input.return_value = "fg"  # bypassing mandatory user input for Fridge or ColdStorage object creation
            storage_conditions = [
                StorageCondition.create_from_(file) for file in file_list
            ]
        temp_spikes = analytical_service.analyze_spikes(storage_conditions)
        reporting_service.report_spikes(temp_spikes)


if __name__ == "__main__":
    unittest.main()
