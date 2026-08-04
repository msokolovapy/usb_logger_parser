import datetime
import unittest
from unittest.mock import Mock, MagicMock
from unittest.mock import patch
import pandas as pd
from pandas import Timestamp
from xlsxwriter import Workbook
import logging
from pathlib import Path

from usb_logger_parser.helper_functions import (
    read,
    parse_,
    get_user_confirmation,
    validate_and_convert,
    get_average_temp,
    get_extreme_date_time,
    get_extreme_temp,
    get_spike_duration,
    convert_timestamps,
    data_collection_frequency_check,
    get_ave_data_coll_freq,
    extract_to_list,
    insert_metadata_header,
    get_files,
    missing_column_check,
    read_convert_headers,
    convert_dtypes,
)
from usb_logger_parser.storage_units import (
    StorageCondition,
    Fridge,
    create_storage_condition_manually,
)
from usb_logger_parser.analytical_service import AnalyticalService
from usb_logger_parser.reporting_service import (
    ReportingService,
    XLSXGraph,
    XLSXSummary,
)

logger = logging.getLogger(__name__)

SAMPLE_DF = pd.DataFrame(
    {
        "ACP169 BU_FZ156": [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
        ],
        "Time": [
            Timestamp("2020-03-16 10:30:00"),
            Timestamp("2020-03-16 10:40:00"),
            Timestamp("2020-03-16 10:50:00"),
            Timestamp("2020-03-16 11:00:00"),
            Timestamp("2020-03-16 11:10:00"),
            Timestamp("2020-03-16 11:20:00"),
            Timestamp("2020-03-16 11:30:00"),
            Timestamp("2020-03-16 11:40:00"),
            Timestamp("2020-03-16 11:50:00"),
            Timestamp("2020-03-16 12:00:00"),
            Timestamp("2020-03-16 12:10:00"),
            Timestamp("2020-03-16 12:20:00"),
            Timestamp("2020-03-16 12:30:00"),
            Timestamp("2020-03-16 12:40:00"),
            Timestamp("2020-03-16 12:50:00"),
            Timestamp("2020-03-16 13:00:00"),
            Timestamp("2020-03-16 13:10:00"),
            Timestamp("2020-03-16 13:20:00"),
            Timestamp("2020-03-16 13:30:00"),
            Timestamp("2020-03-16 13:40:00"),
        ],
        "Celsius(°C)": [
            0.0,
            0.5,
            1.0,
            1.5,
            2.0,
            2.5,
            3.5,
            4.5,
            5.0,
            6.0,
            9.0,
            10.0,
            9.0,
            9.5,
            8.5,
            7.0,
            7.3,
            6.0,
            5.5,
            5.0,
        ],
        "High Alarm": [-4.5] * 20,
        "Low Alarm": [-25.5] * 20,
        "Serial Number": ["052297777"] + [None] * 19,
    }
)


class TestColdChainUnit(unittest.TestCase):
    def setUp(self):
        self.df_temp_data = SAMPLE_DF
        self.logger_id = "ACPL01"
        self.serial_numb = "00001"
        self.ave_data_coll_freq = 152.0
        self.file_basename = "ACPL234_ACPL01_09Apr2026"

    def tearDown(self):
        pass

    def test_cc_unit_init(self):
        file = "dummy.txt"
        with (
            patch("usb_logger_parser.storage_units.read") as mock_read,
            patch(
                "usb_logger_parser.storage_units.get_ave_data_coll_freq"
            ) as mock_ave_data_coll_freq,
            patch(
                "usb_logger_parser.storage_units.get_average_temp"
            ) as mock_get_ave_temp,
            patch(
                "usb_logger_parser.storage_units.get_user_confirmation"
            ) as mock_user_confirmation,
            patch(
                "usb_logger_parser.storage_units.create_storage_condition_manually"
            ) as mock_manual_create,
        ):
            mock_read.return_value = (
                "df_temp_data",
                "logger_id",
                "serial_numb",
                "file_basename",
            )
            mock_ave_data_coll_freq.return_value = "ave_data_coll_freq"

            with self.subTest():
                mock_get_ave_temp.return_value = 5.0
                mock_user_confirmation.side_effect = ["wrong entry", "FG"]

                unit = StorageCondition.create_from_(file)
                mock_read.assert_called_with(file)
                mock_get_ave_temp.assert_called_with("df_temp_data")
                mock_ave_data_coll_freq.assert_called_with("df_temp_data")
                mock_user_confirmation.assert_called()

            with self.subTest():
                mock_get_ave_temp.return_value = 999.9

                unit = StorageCondition.create_from_(file)
                mock_read.assert_called_with(file)
                mock_get_ave_temp.assert_called_with("df_temp_data")
                mock_ave_data_coll_freq.assert_called_with("df_temp_data")
                mock_manual_create.assert_called()

    def test_create_cc_unit(self):
        with (
            patch("usb_logger_parser.storage_units.read") as mock_read,
            patch(
                "usb_logger_parser.storage_units.get_ave_data_coll_freq"
            ) as mock_ave_data_coll_freq,
            patch(
                "usb_logger_parser.storage_units.get_average_temp"
            ) as mock_get_ave_temp,
            patch(
                "usb_logger_parser.storage_units.get_user_confirmation"
            ) as mock_user_confirmation,
        ):

            mock_read.return_value = (
                "df_temp_data",
                "ACPL01",
                "000001",
                "file_basename",
            )
            mock_get_ave_temp.return_value = 50.0

            unit = StorageCondition.create_from_("dummy.txt")

            self.assertIsNotNone(unit)
            self.assertEqual(unit.low_alarm, 45.0)
            self.assertEqual(unit.high_alarm, 55.0)
            self.assertEqual(unit.spike_duration, 15)
            self.assertEqual(unit.logger.id, "ACPL01")
            self.assertEqual(unit.logger.serial_numb, "000001")
            self.assertEqual(unit.file_basename, "file_basename")
            self.assertEqual(
                unit.metadata,
                [
                    ["usb_logger_id", "ACPL01"],
                    ["usb_logger_serial_number", "000001"],
                    ["file_name", "file_basename"],
                ],
            )


class TestHelperFunctions(unittest.TestCase):
    def setUp(self):
        self.file_basename = "ACPL234_ACPL01_09Apr2026"
        self.df_temp_data = SAMPLE_DF
        self.logger_id = "ACP169 BU_FZ156"
        self.serial_numb = "052297777"
        self.ave_data_coll_freq = 10.0
        self.unit = Fridge(
            self.df_temp_data,
            self.logger_id,
            self.serial_numb,
            self.ave_data_coll_freq,
            self.file_basename,
        )

    def tearDown(self):
        pass

    @patch("builtins.input")
    def test_create_storage_condition_manually(self, mock_input):
        mock_input.side_effect = ["abracadabra", "FG"]
        storage_condit = create_storage_condition_manually(
            self.df_temp_data,
            self.logger_id,
            self.serial_numb,
            self.ave_data_coll_freq,
            self.file_basename,
        )
        self.assertIsNotNone(storage_condit)
        self.assertEqual(storage_condit.high_alert, 15.0)

    def test_validate_and_convert(self):
        fail_test_cases = [
            (
                "empty_dataframe",
                pd.DataFrame(),
                ValueError,
                "Empty dataframe when trying to load dummy.txt",
            ),
            (
                "missing_columns",
                pd.DataFrame({"dummy_column": [1, 2, 3, 4]}),
                KeyError,
                "Some columns are missing: Time, Celsius",
            ),
            (
                "missing_value",
                pd.DataFrame({"Time": [1, 2, None, 4], "Celsius": [1, 2, 3, 4]}),
                ValueError,
                "Some values are missing in 'Time' column",
            ),
        ]

        for test, mock_return_value, error, error_message in fail_test_cases:
            with self.subTest(test):
                with patch(
                    "usb_logger_parser.helper_functions.pd.read_csv"
                ) as mock_read_csv:
                    mock_read_csv.return_value = mock_return_value
                    with self.assertRaises(error) as context:
                        validate_and_convert("dummy.txt")
                self.assertIn(error_message, str(context.exception))

        with self.subTest("any other random exception"):
            with patch(
                "usb_logger_parser.helper_functions.pd.read_csv"
            ) as mock_read_csv:
                mock_read_csv.side_effect = pd.errors.ParserError
                with self.assertRaises(pd.errors.ParserError):
                    validate_and_convert("file that raises an exception.txt")

        with self.subTest("validate_and_convert successful"):
            with (
                patch(
                    "usb_logger_parser.helper_functions.pd.read_csv"
                ) as mock_read_csv,
                patch(
                    "usb_logger_parser.helper_functions.missing_column_check"
                ) as mock_missing_column_check,
                patch(
                    "usb_logger_parser.helper_functions.convert_dtypes"
                ) as mock_convert_dtypes,
            ):
                mock_read_csv.return_value = pd.DataFrame(
                    {"Time": [1, 2, 3], "Celsius": [1, 2, 3]}
                )
                mock_missing_column_check.return_value = []
                mock_convert_dtypes.return_value = "df"
                result = validate_and_convert("dummy.txt")

                mock_read_csv.assert_called_with("dummy.txt", encoding="latin-1")
                mock_missing_column_check.assert_called()
                mock_convert_dtypes.assert_called()
                self.assertEqual(result, "df")

    def test_get_average_temp(self):
        df = pd.DataFrame({"celsius": [-25.0, -26.0, -24.0, -23.0]})
        average_temp = get_average_temp(df)
        self.assertEqual(average_temp, -24.5)

    def test_parse_(self):
        df = pd.DataFrame(
            {
                "ACPL01": [1, 2, 3, 4],
                "Time": [
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                ],
                "Celsius": [0.0, 2.0, 3.0, 2.0],
                "High Alarm": [10.0, 10.0, 10.0, 10.0],
                "Low Alarm": [0.0, 0.0, 0.0, 0.0],
                "Serial Number": ["0000123", None, None, None],
            }
        )
        df_result, logger_id, serial_numb = parse_(df)
        with self.subTest("parsing df"):
            expected = {
                "row_numb": [1, 2, 3, 4],
                "date_time": [
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                ],
                "celsius": [0.0, 2.0, 3.0, 2.0],
                "high_alarm": [10.0, 10.0, 10.0, 10.0],
                "low_alarm": [0.0, 0.0, 0.0, 0.0],
            }
            self.assertEqual(df_result.to_dict("list"), expected)
        with self.subTest("parsing logger id"):
            self.assertEqual(logger_id, "ACPL01")
        with self.subTest("parsing serial number"):
            self.assertEqual(serial_numb, "0000123")

    def test_read(self):
        with (
            patch(
                "usb_logger_parser.helper_functions.validate_and_convert"
            ) as mock_valid_df,
            patch("usb_logger_parser.helper_functions.parse_") as mock_parse,
        ):
            mock_traversable_obj = MagicMock()
            mock_traversable_obj.name = self.file_basename
            mock_traversable_obj.open.return_value.__enter__.return_value = "file"
            mock_valid_df.return_value = "valid_dataframe"
            mock_parse.return_value = ("df", "ACP169 BU_FZ156", "052297777")

            df_temp_data, logger_id, serial_numb, file_basename = read(
                mock_traversable_obj
            )

            mock_valid_df.assert_called_with("file")
            mock_parse.assert_called_with("valid_dataframe")
            self.assertEqual(df_temp_data, "df")
            self.assertEqual(logger_id, "ACP169 BU_FZ156")
            self.assertEqual(serial_numb, "052297777")
            self.assertEqual(file_basename, self.file_basename)

    def test_get_extreme_temp(self):
        sample_df_slice = pd.DataFrame({"celsius": [-25.0, -26.0, -24.0, -23.0]})
        extreme_temp = get_extreme_temp(sample_df_slice).iloc[0, 0]

        self.assertEqual(extreme_temp, -26.0)

    def test_get_extreme_date_time(self):
        sample_df_slice = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:40:00"),
                ]
            }
        )
        sample_df = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:40:00"),
                ],
                "celsius": [-25.0, -26.0, -24.0, -23.0],
            }
        )

        extreme_date_time = get_extreme_date_time(sample_df_slice, sample_df).iloc[0]
        self.assertEqual(extreme_date_time, Timestamp("2020-03-15 10:30:00"))

    def test_get_spike_duration(self):
        sample_df_slice = pd.Series(
            [
                Timestamp("2020-03-15 10:20:00"),
                Timestamp("2020-03-15 10:30:00"),
                Timestamp("2020-03-15 10:40:00"),
                Timestamp("2020-03-16 10:40:00"),
            ]
        )
        spike_duration = get_spike_duration(sample_df_slice)
        self.assertEqual(spike_duration, 1460)

    def test_data_collection_frequency_check(self):
        units_pass = [Mock() for _ in range(4)]
        freq_pass = 10.0
        for mock_unit in units_pass:
            mock_unit.logger.ave_data_coll_freq = freq_pass

        units_fail = [Mock() for _ in range(4)]
        fail_dict = [
            (10.0, "ACPL01"),
            (10.0, "ACPL02"),
            (10.0, "ACPL03"),
            (20.3, "ACPL04"),
        ]
        for mock_unit, attributes in zip(units_fail, fail_dict):
            ave_data_coll_freq, logger_id = attributes
            mock_unit.logger.ave_data_coll_freq = ave_data_coll_freq
            mock_unit.logger.id = logger_id

        result = data_collection_frequency_check(units_pass)
        self.assertTrue(result)
        with self.assertRaises(ValueError):
            result = data_collection_frequency_check(units_fail)

    def test_get_ave_data_coll_freq(self):
        df = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                    Timestamp("2020-03-16 11:20:00"),
                    Timestamp("2020-03-16 11:30:00"),
                    Timestamp("2020-03-16 11:40:00"),
                ]
            }
        )
        result = get_ave_data_coll_freq(df)
        self.assertEqual(result, 152.0)

    def test_insert_metadata_header(self):
        metadata_list = [
            ["usb_logger_id", "ACPL01"],
            ["usb_logger_serial_number", "000001"],
            ["file_name", "file_basename"],
        ]
        data = [
            ["row_numb", "date_time", "celsius"],
            [1, Timestamp("2020-03-16 10:30:00"), 0.0],
            [2, Timestamp("2020-03-16 10:40:00"), 2.0],
            [3, Timestamp("2020-03-16 10:50:00"), 3.0],
            [4, Timestamp("2020-03-16 11:00:00"), 2.0],
        ]
        result = insert_metadata_header(data, metadata_list)
        expected = [
            ["file_name", "file_basename"],
            ["usb_logger_serial_number", "000001"],
            ["usb_logger_id", "ACPL01"],
            ["row_numb", "date_time", "celsius"],
            [1, Timestamp("2020-03-16 10:30:00"), 0.0],
            [2, Timestamp("2020-03-16 10:40:00"), 2.0],
            [3, Timestamp("2020-03-16 10:50:00"), 3.0],
            [4, Timestamp("2020-03-16 11:00:00"), 2.0],
        ]
        self.assertEqual(result, expected)

    def test_extract_to_list(self):
        df = pd.DataFrame(
            {
                "row_numb": [1, 2, 3, 4],
                "date_time": [
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                ],
                "celsius": [0.0, 2.0, 3.0, 2.0],
            }
        )
        result = extract_to_list(df)
        expected = [
            ["row_numb", "date_time", "celsius"],
            [1, Timestamp("2020-03-16 10:30:00"), 0.0],
            [2, Timestamp("2020-03-16 10:40:00"), 2.0],
            [3, Timestamp("2020-03-16 10:50:00"), 3.0],
            [4, Timestamp("2020-03-16 11:00:00"), 2.0],
        ]
        self.assertEqual(result, expected)

    def test_convert_timestamps(self):
        df = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-15 12:00:00"),
                    Timestamp("2020-03-15 12:10:00"),
                    Timestamp("2020-03-15 12:20:00"),
                ],
                "date": [
                    Timestamp("2020-03-15"),
                    Timestamp("2020-03-15"),
                    Timestamp("2020-03-15 "),
                ],
            }
        )
        result = convert_timestamps(df)
        expected = {
            "date_time": [
                datetime.datetime(2020, 3, 15, 12),
                datetime.datetime(2020, 3, 15, 12, 10),
                datetime.datetime(2020, 3, 15, 12, 20),
            ],
            "date": [
                datetime.datetime(2020, 3, 15),
                datetime.datetime(2020, 3, 15),
                datetime.datetime(2020, 3, 15),
            ],
        }
        self.assertEqual(expected, result.to_dict("list"))

    def test_get_files(self):
        with patch("usb_logger_parser.helper_functions.files") as mock_importlib_files:
            with self.subTest("importlib unexpected error"):
                mock_importlib_files.return_value = None
                with self.assertRaises(Exception) as ctx:
                    get_files("usb_logger_parser", "resources")
                self.assertIn(
                    "Unexpected error when trying to access usb_logger_parser.resources",
                    str(ctx.exception),
                )
                mock_importlib_files.reset_mock(return_value=True)

            with self.subTest("importlib ValueError"):
                with self.assertRaises(ValueError) as ctx:
                    get_files("dummy_1", "dummy_2")
                self.assertIn(
                    'No raw temperature data files found in "dummy_2" directory',
                    str(ctx.exception),
                )
                mock_importlib_files.reset_mock()

            with self.subTest("importlib works fine"):
                mock_file = Mock()
                mock_file.is_file.return_value = True
                mock_importlib_files.return_value.joinpath.return_value.iterdir.return_value = iter(
                    [mock_file]
                )
                file = get_files("usb_logger_parser", "resources")

                mock_importlib_files.assert_called_with("usb_logger_parser")
                mock_importlib_files.return_value.joinpath.assert_called_with(
                    "resources"
                )
                self.assertEqual(file, [mock_file])

    def test_missing_column_check(self):
        test_cases = [
            (
                "missing column check pass",
                ["ACPL211 StbFG", "Time", "Celsius(ï¿½C)", "Serial Number"],
                [],
            ),
            (
                "missing column check fail",
                ["ACPL211 StbFG", "Serial Number"],
                ["Time", "Celsius"],
            ),
        ]
        required_cols = ["Time", "Celsius"]

        for test_name, case, expected in test_cases:
            with self.subTest(test_name):
                result = missing_column_check(case, required_cols)
                self.assertEqual(result, expected)
        with self.subTest("missing column check - raising AttributeError"):
            with self.assertRaises(AttributeError) as context:
                result = missing_column_check([1, 2, 3, 4], required_cols)
            self.assertIn(
                "Failed to convert column names to lower-case", str(context.exception)
            )
        with self.subTest("missing column check - raising general Exception"):
            with self.assertRaises(Exception) as context:
                bad_result = Mock()
                bad_result.lower.side_effect = RuntimeError()
                result = missing_column_check([bad_result], required_cols)
            self.assertIn(
                "Unknown error when trying to convert column names to lower-case",
                str(context.exception),
            )

    def test_convert_dtypes(self):
        with self.subTest("convert_dtypes successful"):
            df = pd.DataFrame(
                {
                    "Serial Number": ["0215489PNW"],
                    "Celsius": ["1.1"],
                    "High Alarm": ["1.1"],
                    "Low Alarm": ["1.1"],
                    "Time": ["2020-03-20 10:00:00"],
                }
            )

            expected = {
                "Serial Number": ["0215489PNW"],
                "Celsius": [1.1],
                "High Alarm": [1.1],
                "Low Alarm": [1.1],
                "Time": [Timestamp("2020-03-20 10:00:00")],
            }

            result = convert_dtypes(df)
            self.assertEqual(result.to_dict("list"), expected)

        with self.subTest("convert_dtypes raises ValueError"):
            df = pd.DataFrame(
                {
                    "Serial Number": ["0215489PNW", None],
                    "Celsius": ["abc", "1.2"],
                    "High Alarm": ["1.1", "1.2"],
                    "Low Alarm": ["1.1", "1.2"],
                    "Time": ["2020-03-20 10:00:00", "2020-03-20 10:15:00"],
                }
            )
            with self.assertRaises(ValueError) as context:
                result = convert_dtypes(df)
            self.assertIn(
                f"Failed to convert column 'Celsius' using {float}",
                str(context.exception),
            )

    def test_read_convert_headers(self):
        with self.subTest("read_convert_headers successful"):
            df = pd.DataFrame(
                {
                    "Time": [],
                    "Celsius(ï¿½C)": [],
                    "High Alarm": [],
                    "Low Alarm": [],
                    "Serial Number": [],
                    "License ÂNo": [],
                }
            )
            expected = [
                "Time",
                "Celsius",
                "High Alarm",
                "Low Alarm",
                "Serial Number",
                "License ÂNo",
            ]
            result = df.columns.map(read_convert_headers)
            self.assertEqual(list(result), expected)

        with self.subTest("read_convert_headers raises AttributeError"):
            df = pd.DataFrame({1.2: [], "Celsius": []})
            with self.assertRaises(AttributeError) as context:
                result = df.columns.map(read_convert_headers)
            self.assertIn(
                "Failed to convert header '1.2' to an expected header",
                str(context.exception),
            )

        with self.subTest("read_convert_headers raises Exception"):
            bad_header = Mock()
            bad_header.lower.side_effect = RuntimeError()
            with self.assertRaises(Exception) as context:
                read_convert_headers(bad_header)
            self.assertIn(
                "Unexpected error occured when trying to convert header",
                str(context.exception),
            )


class TestAnalyticalServiceInit(unittest.TestCase):
    def test_analyt_service_init(self):
        analytical_service = AnalyticalService()
        self.assertIsNotNone(analytical_service.analyze_spikes)


class TestAnalyticalService(unittest.TestCase):
    def setUp(self):
        self.analytical_service = AnalyticalService()
        df_temp_data = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                ],
                "celsius": [
                    0.0,
                    0.5,
                    1.0,
                    1.5,
                    2.0,
                ],
            }
        )
        self.unit = Fridge(
            df_temp_data,
            logger_id="ACP169 BU_FZ156",
            serial_numb="052297777",
            ave_data_coll_freq=152.0,
            file_basename="dummy.txt",
        )

    def tearDown(self):
        pass

    def test_analyze_spikes(self):
        with (
            patch.object(AnalyticalService, "add_status_column") as mock_add_status,
            patch.object(AnalyticalService, "add_cumulat_spike_id") as mock_cumulat_id,
            patch.object(
                AnalyticalService, "prepare_df_last_spike_of_day"
            ) as mock_last_spike,
            patch.object(AnalyticalService, "get_extremes_info") as mock_extremes,
            patch.object(
                AnalyticalService, "prepare_excursions_df"
            ) as mock_excursions_df,
            patch.object(AnalyticalService, "renumber_spikes") as mock_renumber_spikes,
            patch.object(
                AnalyticalService, "check_against_limits"
            ) as mock_check_limits,
            patch.object(AnalyticalService, "find_mkt") as mock_mkt,
            patch.object(
                AnalyticalService, "prepare_spike_summary_for_reporting"
            ) as mock_prepare_for_reporting,
        ):
            mock_add_status.return_value = "df_added_status"
            mock_cumulat_id.return_value = "df_with_cumulat_spike_id"
            mock_last_spike.return_value = "df_last_spike_added"
            mock_extremes.return_value = "df_extremes"
            mock_excursions_df.return_value = "df_excursions"
            mock_renumber_spikes.return_value = "df_renumbered_spikes"
            mock_check_limits.return_value = "df_checked_against_limits"
            mock_mkt.return_value = "spike_dict_mkt_calculated"
            mock_prepare_for_reporting.return_value = "spikes_prepared_for_reporting"

            result = self.analytical_service.analyze_spikes([self.unit])

            pd.testing.assert_frame_equal(
                mock_add_status.call_args[0][0], self.unit.temp_data
            )
            self.assertEqual(mock_add_status.call_args[0][1], 2.0)
            self.assertEqual(mock_add_status.call_args[0][2], 8.0)

            mock_cumulat_id.assert_called_with("df_added_status")
            mock_last_spike.assert_called_with("df_with_cumulat_spike_id")
            mock_extremes.assert_called_with("df_with_cumulat_spike_id")
            mock_excursions_df.assert_called_with("df_last_spike_added", "df_extremes")
            mock_renumber_spikes.assert_called_with("df_excursions")
            mock_check_limits.assert_called_with(
                "df_renumbered_spikes",
                self.unit.spike_duration,
                self.unit.total_spikes_duration,
            )
            mock_mkt.assert_called_with(
                "df_checked_against_limits", self.unit.temp_data
            )
            mock_prepare_for_reporting.assert_called_with(
                "spike_dict_mkt_calculated",
                [
                    ["usb_logger_id", "ACP169 BU_FZ156"],
                    ["usb_logger_serial_number", "052297777"],
                    ["file_name", "dummy.txt"],
                ],
            )

            self.assertEqual(result, ["spikes_prepared_for_reporting"])

    def test_add_status_column(self):
        sample_df = pd.DataFrame(
            {
                "date_time": [
                    "2020-03-15 10:20:00",
                    "2020-03-15 10:30:00",
                    "2020-03-15 10:40:00",
                    "2020-03-16 10:30:00",
                    "2020-03-16 10:40:00",
                    "2020-03-16 10:50:00",
                    "2020-03-16 11:00:00",
                    "2020-03-16 11:10:00",
                    "2020-03-16 11:20:00",
                    "2020-03-16 11:30:00",
                    "2020-03-16 11:40:00",
                ],
                "celsius": [16.0, 20.0, 16.0, 5.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5],
            }
        )
        df_added_status = self.analytical_service.add_status_column(
            sample_df, self.unit.low_alarm, self.unit.high_alarm
        )
        self.assertIn("status", df_added_status.columns)

    def test_add_cumulat_spike_id(self):
        sample_df = pd.DataFrame(
            {
                "date_time": [
                    "2020-03-15 10:20:00",
                    "2020-03-15 10:30:00",
                    "2020-03-15 10:40:00",
                    "2020-03-16 10:30:00",
                    "2020-03-16 10:40:00",
                    "2020-03-16 10:50:00",
                    "2020-03-16 11:00:00",
                    "2020-03-16 11:10:00",
                    "2020-03-16 11:20:00",
                    "2020-03-16 11:30:00",
                    "2020-03-16 11:40:00",
                ],
                "celsius": [16.0, 20.0, 16.0, 5.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5],
                "status": [
                    "too_high",
                    "too_high",
                    "too_high",
                    None,
                    "too_low",
                    "too_low",
                    "too_low",
                    "too_low",
                    None,
                    None,
                    None,
                ],
            }
        )
        df_cumulat_spike_id = self.analytical_service.add_cumulat_spike_id(sample_df)
        self.assertIn("cumulat_spike_id", df_cumulat_spike_id.columns)
        self.assertEqual(df_cumulat_spike_id["cumulat_spike_id"][0], 1)

    def test_add_gap_mins(self):
        sample_df = pd.DataFrame(
            {
                "date_time": [
                    "2020-03-15 10:20:00",
                    "2020-03-15 10:30:00",
                    "2020-03-15 10:40:00",
                    "2020-03-16 10:30:00",
                    "2020-03-16 10:40:00",
                    "2020-03-16 10:50:00",
                    "2020-03-16 11:00:00",
                    "2020-03-16 11:10:00",
                    "2020-03-16 11:20:00",
                    "2020-03-16 11:30:00",
                    "2020-03-16 11:40:00",
                ],
                "cumulat_spike_id": [1, 1, 1, 2, 3, 3, 3, 3, 4, 5, 6],
                "status": [
                    "too_high",
                    "too_high",
                    "too_high",
                    None,
                    "too_low",
                    "too_low",
                    "too_low",
                    "too_low",
                    None,
                    None,
                    None,
                ],
            }
        )
        sample_df["date_time"] = pd.to_datetime(sample_df["date_time"])
        df = self.analytical_service.add_gap_mins(sample_df)

        self.assertIn("reading_gap_mins", df.columns)
        self.assertTrue((df["reading_gap_mins"] == 10).any())

    def test_prepare_df_last_spike_of_day(self):
        with (
            patch.object(AnalyticalService, "add_gap_mins") as mock_gap_mins,
            patch.object(AnalyticalService, "filter_by_status") as mock_status_filter,
            patch.object(AnalyticalService, "add_last_spike_check") as mock_last_spike,
            patch.object(
                AnalyticalService, "prepare_24hr_window_start"
            ) as mock_24hr_window,
            patch.object(
                AnalyticalService, "filter_by_last_spike"
            ) as mock_spike_filter,
            patch.object(
                AnalyticalService, "determine_spike_duration_24hr_mins"
            ) as mock_last_spike_df,
        ):
            mock_gap_mins.return_value = "df_gap_mins_added"
            mock_status_filter.return_value = "df_filtered_by_status"
            mock_last_spike.return_value = "last_spike_added"
            mock_24hr_window.return_value = "24hr_window_added"
            mock_spike_filter.return_value = "df_filtered_by_last_spike"
            mock_last_spike_df.return_value = "df_spike_duration_24hr_added"

            last_spike_df = self.analytical_service.prepare_df_last_spike_of_day(
                "original_df"
            )

            mock_gap_mins.assert_called_with("original_df")
            mock_status_filter.assert_called_with("df_gap_mins_added")
            mock_last_spike.assert_called_with("df_filtered_by_status")
            mock_24hr_window.assert_called_with("last_spike_added")
            mock_spike_filter.assert_called_with("24hr_window_added")
            mock_last_spike_df.assert_called_with(
                "df_filtered_by_last_spike", "original_df"
            )

            self.assertEqual(last_spike_df, "df_spike_duration_24hr_added")

    def test_filter_by_status(self):
        sample_df = pd.DataFrame(
            {
                "date_time": [
                    "2020-03-15 10:20:00",
                    "2020-03-15 10:30:00",
                    "2020-03-15 10:40:00",
                    "2020-03-16 10:30:00",
                    "2020-03-16 10:40:00",
                    "2020-03-16 10:50:00",
                    "2020-03-16 11:00:00",
                    "2020-03-16 11:10:00",
                    "2020-03-16 11:20:00",
                    "2020-03-16 11:30:00",
                    "2020-03-16 11:40:00",
                ],
                "celsius": [16.0, 20.0, 16.0, 5.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5],
                "status": [
                    "too_high",
                    "too_high",
                    "too_high",
                    None,
                    "too_low",
                    "too_low",
                    "too_low",
                    "too_low",
                    None,
                    None,
                    None,
                ],
                "cumulat_spike_id": [1, 1, 1, 2, 3, 3, 3, 3, 4, 5, 6],
            }
        )

        df_filtered = self.analytical_service.filter_by_status(sample_df)
        self.assertTrue((df_filtered["status"] != None).all())

    def test_add_last_spike_check(self):
        sample_df = pd.DataFrame(
            {
                "cumulat_spike_id": [1, 1, 1, 3, 3, 3, 3],
                "date_time": [
                    "2020-03-15 10:20:00",
                    "2020-03-15 10:30:00",
                    "2020-03-15 10:40:00",
                    "2020-03-16 10:40:00",
                    "2020-03-16 10:50:00",
                    "2020-03-16 11:00:00",
                    "2020-03-16 11:10:00",
                ],
                "celsius": [16.0, 20.0, 16.0, 0.0, 0.5, 1.0, 1.5],
                "status": [
                    "too_high",
                    "too_high",
                    "too_high",
                    "too_low",
                    "too_low",
                    "too_low",
                    "too_low",
                ],
            }
        )
        sample_df["date_time"] = pd.to_datetime(sample_df["date_time"])

        df_last_spike = self.analytical_service.add_last_spike_check(sample_df)
        self.assertEqual(
            df_last_spike["last_spike_of_day"].to_list(),
            [False, False, True, False, False, False, True],
        )

    def test_prepare_24hr_window_start(self):
        sample_df = pd.DataFrame(
            {
                "cumulat_spike_id": [1, 1, 1, 3, 3, 3, 3],
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                ],
                "celsius": [16.0, 20.0, 16.0, 0.0, 0.5, 1.0, 1.5],
                "status": [
                    "too_high",
                    "too_high",
                    "too_high",
                    "too_low",
                    "too_low",
                    "too_low",
                    "too_low",
                ],
                "last_spike_of_day": [False, False, True, False, False, False, True],
            }
        )
        expected_values = [
            Timestamp("2020-03-14 10:20:00"),
            Timestamp("2020-03-14 10:30:00"),
            Timestamp("2020-03-14 10:40:00"),
            Timestamp("2020-03-15 10:40:00"),
            Timestamp("2020-03-15 10:50:00"),
            Timestamp("2020-03-15 11:00:00"),
            Timestamp("2020-03-15 11:10:00"),
        ]

        df_24hr_window = self.analytical_service.prepare_24hr_window_start(sample_df)
        self.assertEqual(df_24hr_window["24hr_window_start"].to_list(), expected_values)

    def test_filter_by_spike(self):
        sample_df = pd.DataFrame(
            {
                "cumulat_spike_id": [1, 1, 1, 3, 3, 3, 3],
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                ],
                "celsius": [16.0, 20.0, 16.0, 0.0, 0.5, 1.0, 1.5],
                "status": [
                    "too_high",
                    "too_high",
                    "too_high",
                    "too_low",
                    "too_low",
                    "too_low",
                    "too_low",
                ],
                "last_spike_of_day": [False, False, True, False, False, False, True],
                "24hr_window_start": [
                    Timestamp("2020-03-14 10:20:00"),
                    Timestamp("2020-03-14 10:30:00"),
                    Timestamp("2020-03-14 10:40:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-15 10:50:00"),
                    Timestamp("2020-03-15 11:00:00"),
                    Timestamp("2020-03-15 11:10:00"),
                ],
            }
        )
        df_grouped = self.analytical_service.filter_by_last_spike(sample_df)
        expected_columns = [
            "cumulat_spike_id",
            "date_time",
            "last_spike_of_day",
            "24hr_window_start",
        ]

        self.assertTrue((df_grouped["last_spike_of_day"] == True).all())
        self.assertEqual(list(df_grouped.columns), expected_columns)

    def test_spike_duration_in_24hr_window(self):
        df = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                    Timestamp("2020-03-16 11:20:00"),
                    Timestamp("2020-03-16 11:30:00"),
                    Timestamp("2020-03-16 11:40:00"),
                ],
                "status": [
                    "too_high",
                    "too_high",
                    "too_high",
                    None,
                    "too_low",
                    "too_low",
                    "too_low",
                    "too_low",
                    None,
                    None,
                    None,
                ],
                "reading_gap_mins": [
                    None,
                    10.0,
                    10.0,
                    None,
                    None,
                    10.0,
                    10.0,
                    10.0,
                    None,
                    None,
                    None,
                ],
            }
        )
        tests = [
            (
                {
                    "date_time": Timestamp("2020-03-15 10:40:00"),
                    "24hr_window_start": Timestamp("2020-03-14 10:40:00"),
                },
                20,
            ),
            (
                {
                    "date_time": Timestamp("2020-03-16 11:10:00"),
                    "24hr_window_start": Timestamp("2020-03-15 11:10:00"),
                },
                30,
            ),
        ]

        for data, expected_duration in tests:
            with self.subTest(data):
                result = self.analytical_service.spike_duration_in_24hr_window(
                    pd.Series(data), df
                )
                self.assertEqual(result, expected_duration)

    def test_determine_spike_duration_24hr_mins(self):
        with patch.object(
            AnalyticalService, "spike_duration_in_24hr_window", autospec=True
        ) as mock_spike_duration:
            self.analytical_service.determine_spike_duration_24hr_mins(
                pd.DataFrame({}), pd.DataFrame({})
            )
            mock_spike_duration.assert_called()

    def test_get_extremes_info(self):
        sample_df = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                    Timestamp("2020-03-16 11:20:00"),
                    Timestamp("2020-03-16 11:30:00"),
                    Timestamp("2020-03-16 11:40:00"),
                ],
                "celsius": [16.0, 20.0, 16.0, 5.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5],
                "status": [
                    "too_high",
                    "too_high",
                    "too_high",
                    None,
                    "too_low",
                    "too_low",
                    "too_low",
                    "too_low",
                    None,
                    None,
                    None,
                ],
                "cumulat_spike_id": [1, 1, 1, 2, 3, 3, 3, 3, 4, 5, 6],
            }
        )
        df_excursions = self.analytical_service.get_extremes_info(sample_df)
        expected_spike_duration_mins = [20, 30]
        expected_extreme_temps = [20.0, 1.5]

        self.assertEqual(
            df_excursions["spike_duration_mins"].to_list(), expected_spike_duration_mins
        )
        self.assertEqual(
            df_excursions["extreme_temp"].to_list(), expected_extreme_temps
        )

    def test_prepare_excursions_df(self):
        df_excursions = pd.DataFrame(
            {
                "cumulat_spike_id": [1, 3],
                "extreme_temp": [20.0, 1.5],
                "spike_date": [Timestamp("2020-03-15"), Timestamp("2020-03-16")],
                "extreme_date_time": [
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-16 11:10:00"),
                ],
                "spike_duration_mins": [20, 30],
            }
        )

        df_total_spike_duration = pd.DataFrame(
            {
                "cumulat_spike_id": [1, 3],
                "date_time": [
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-16 11:10:00"),
                ],
                "24hr_window_start": [
                    Timestamp("2020-03-14 10:30:00"),
                    Timestamp("2020-03-15 11:10:00"),
                ],
                "spike_duration_24hr_mins": [20.0, 30.0],
            }
        )
        df_merged = self.analytical_service.prepare_excursions_df(
            df_total_spike_duration, df_excursions
        )
        expected_result = {
            "cumulat_spike_id": [1, 3],
            "extreme_temp": [20.0, 1.5],
            "spike_date": [Timestamp("2020-03-15"), Timestamp("2020-03-16")],
            "extreme_date_time": [
                Timestamp("2020-03-15 10:30:00"),
                Timestamp("2020-03-16 11:10:00"),
            ],
            "spike_duration_mins": [20, 30],
            "spike_duration_24hr_mins": [20.0, 30.0],
        }
        self.assertEqual(df_merged.to_dict("list"), expected_result)

    def test_renumber_spikes(self):
        sample_df = pd.DataFrame(
            {
                "cumulat_spike_id": [1, 3],
                "spike_date": [Timestamp("2020-03-15"), Timestamp("2020-03-16")],
            }
        )
        df_spikes_renumbered = self.analytical_service.renumber_spikes(sample_df)
        self.assertIn("spike_number", df_spikes_renumbered.columns)
        self.assertNotIn("cumulat_spike_id", df_spikes_renumbered.columns)
        self.assertTrue(df_spikes_renumbered["spike_number"].dtype == int)
        self.assertEqual(df_spikes_renumbered.columns.get_loc("spike_number"), 0)

    def test_check_against_limits(self):
        df = pd.DataFrame(
            {"spike_duration_mins": [20, 30], "spike_duration_24hr_mins": [20.0, 30.0]}
        )
        df_checked_against_limits = self.analytical_service.check_against_limits(
            df, self.unit.spike_duration, self.unit.total_spikes_duration
        )

        self.assertIn("spike_status", df_checked_against_limits.columns)
        self.assertTrue((df_checked_against_limits["spike_status"] == "Pass").all())

    def test_find_mkt(self):
        with patch.object(
            AnalyticalService, "calculate_mkt_24hr_window", autospec=True
        ) as mock_mkt:
            self.analytical_service.find_mkt(pd.DataFrame({}), pd.DataFrame({}))
            mock_mkt.assert_called()

    def test_calculate_mkt_24hr_window(self):
        sample_row = pd.Series(
            {
                "extreme_date_time": Timestamp("2020-03-16 11:10:00"),
                "spike_status": "Fail",
            }
        )
        sample_df = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                    Timestamp("2020-03-16 11:20:00"),
                    Timestamp("2020-03-16 11:30:00"),
                    Timestamp("2020-03-16 11:40:00"),
                ],
                "celsius": [16.0, 20.0, 16.0, 5.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5],
            }
        )
        result = self.analytical_service.calculate_mkt_24hr_window(
            sample_row, sample_df
        )
        self.assertEqual(result, 2.2)

    def test_apply_arrhenius(self):
        sample_df = pd.DataFrame(
            {
                "date_time": [
                    Timestamp("2020-03-15 10:20:00"),
                    Timestamp("2020-03-15 10:30:00"),
                    Timestamp("2020-03-15 10:40:00"),
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                    Timestamp("2020-03-16 11:20:00"),
                    Timestamp("2020-03-16 11:30:00"),
                    Timestamp("2020-03-16 11:40:00"),
                ],
                "celsius": [16.0, 20.0, 16.0, 5.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5],
            }
        )
        expected_result = 9.6
        result = self.analytical_service.apply_arrhenius(sample_df)
        self.assertEqual(result, expected_result)

    def test_prepare_spike_summary_for_reporting(self):
        with (
            patch(
                "usb_logger_parser.analytical_service.extract_to_list"
            ) as mock_extract_to_list,
            patch(
                "usb_logger_parser.analytical_service.insert_metadata_header"
            ) as mock_insert_metadata_header,
        ):
            df_excursions = MagicMock()
            mock_extract_to_list.return_value = "data_extracted"
            mock_insert_metadata_header.return_value = "data_with_header"
            result = self.analytical_service.prepare_spike_summary_for_reporting(
                df_excursions, "usb_logger_metadata"
            )

            mock_extract_to_list.assert_called_with(df_excursions)
            mock_insert_metadata_header.assert_called_with(
                "data_extracted", "usb_logger_metadata"
            )
            self.assertEqual(result, "data_with_header")


class TestReportingService(unittest.TestCase):
    def setUp(self):
        self.reporting_service = ReportingService()
        df_temp_data = pd.DataFrame(
            {
                "row_numb": [1, 2, 3, 4, 5],
                "date_time": [
                    Timestamp("2020-03-16 10:30:00"),
                    Timestamp("2020-03-16 10:40:00"),
                    Timestamp("2020-03-16 10:50:00"),
                    Timestamp("2020-03-16 11:00:00"),
                    Timestamp("2020-03-16 11:10:00"),
                ],
                "celsius": [
                    0.0,
                    0.5,
                    1.0,
                    1.5,
                    2.0,
                ],
            }
        )
        self.unit = Fridge(
            df_temp_data,
            logger_id="ACP169 BU_FZ156",
            serial_numb="052297777",
            ave_data_coll_freq=152.0,
            file_basename="dummy.txt",
        )

    def tearDown(self):
        pass

    def test_report_raw_data(self):
        sample_data = {
            self.unit: {
                "data": "data_with_header",
                "data_row_min": "data_row_min",
                "data_row_max": "data_row_max",
                "data_width": "data_width",
            }
        }

        with (
            patch.object(
                ReportingService, "prepare_data_for_reporting"
            ) as mock_prepare_data,
            patch.object(XLSXGraph, "insert_data") as mock_insert_data,
            patch.object(XLSXGraph, "insert_chart") as mock_insert_chart,
        ):
            mock_prepare_data.return_value = sample_data
            storage_units = [self.unit]

            result = self.reporting_service.report_raw_data(storage_units)

            mock_prepare_data.assert_called_with(self.unit)
            mock_insert_data.assert_called()
            mock_insert_chart.assert_called()
            self.assertEqual(self.reporting_service.data_to_graph, [sample_data])

    def test_prepare_data_for_reporting_(self):
        with (
            patch(
                "usb_logger_parser.reporting_service.extract_to_list"
            ) as mock_extract_to_list,
            patch(
                "usb_logger_parser.reporting_service.insert_metadata_header"
            ) as mock_insert_metadata_header,
        ):
            mock_extract_to_list.return_value = "data_extracted"
            mock_insert_metadata_header.return_value = "data_with_header"
            result = self.reporting_service.prepare_data_for_reporting(self.unit)
            expected_result = {
                self.unit: {
                    "data": "data_with_header",
                    "data_row_min": 4,
                    "data_row_max": 15,
                    "data_width": 3,
                }
            }
            mock_extract_to_list.assert_called_with(self.unit.temp_data)
            mock_insert_metadata_header.assert_called_with(
                "data_extracted",
                [
                    ["usb_logger_id", self.unit.logger.id],
                    ["usb_logger_serial_number", self.unit.logger.serial_numb],
                    ["file_name", self.unit.file_basename],
                ],
            )
            self.assertEqual(result, expected_result)

    def test_report_spikes(self):
        output_dir = Path("output")
        with patch(
            "usb_logger_parser.reporting_service.XLSXSummary"
        ) as mock_xlsx_summary:
            self.reporting_service.report_spikes("spike_info_list")

            mock_xlsx_summary.assert_called_with("spike_info_list", output_dir, None)
            mock_xlsx_summary.return_value.insert_data.assert_called()


class TestXLSXSummary(unittest.TestCase):
    def test_xlsx_summary_init(self):
        spikes_list = []
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        output_path = None
        output_dir = Path("output")

        result = XLSXSummary(spikes_list, output_dir, output_path)

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.spikes_list)
        self.assertIsNotNone(result.wb)
        self.assertIsNotNone(result.ws)
        self.assertEqual(
            f"{result.file_path}.xlsx", f"{output_dir}/{today}_spikes_summary.xlsx"
        )

    def test_insert_data(self):
        sample_spikes_list = [
            (
                ("file_name", "dummy.txt"),
                ("usb_serial_number", "052297777"),
                ("usb_logger_id", "ACP169 BU_FZ156"),
                (
                    "cumulat_spike_id",
                    "extreme_temp",
                    "spike_date",
                    "extreme_date_time",
                    "spike_duration_mins",
                    "spike_duration_24hr_mins",
                ),
                (
                    1,
                    20.0,
                    datetime.date(2020, 3, 15),
                    datetime.datetime(2020, 3, 15, 10, 30),
                    20,
                    20.0,
                ),
            ),
            (
                ("file_name", "dummy_2.txt"),
                ("usb_serial_number", "064297777"),
                ("usb_logger_id", "ACP226"),
                (
                    "cumulat_spike_id",
                    "extreme_temp",
                    "spike_date",
                    "extreme_date_time",
                    "spike_duration_mins",
                    "spike_duration_24hr_mins",
                ),
                (
                    1,
                    1.5,
                    datetime.date(2020, 3, 16),
                    datetime.datetime(2020, 3, 16, 11, 10),
                    30,
                    30.0,
                ),
            ),
        ]
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        output_path = f"{today}_unittests_spikes_summary"
        output_dir = Path("output")
        xlsx_summary = XLSXSummary(sample_spikes_list, output_dir, output_path)
        xlsx_summary.insert_data()


class TestXLSXGraph(unittest.TestCase):
    def setUp(self):
        self.reporting_service = ReportingService()
        self.unit = Fridge(
            df_temp_data="df_temp_data",
            logger_id="ACP169 BU_FZ156",
            serial_numb="052297777",
            ave_data_coll_freq=152.0,
            file_basename="dummy.txt",
        )

    def tearDown(self):
        pass

    def test_xlsxgraph_init(self):
        data = {
            "unit": {
                "data": "data_with_header",
                "data_row_min": "data_row_min",
                "data_row_max": "data_row_max",
                "data_width": "data_width",
            }
        }
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        output_path = None
        output_dir = Path("output")
        result = XLSXGraph(data, output_dir, output_path)
        self.assertIsNotNone(result)
        self.assertEqual(result.start_col, 10)
        self.assertEqual(
            f"{result.file_path}.xlsx", f"{output_dir}/{today}_usb_loggers_graph.xlsx"
        )
        self.assertEqual(
            result.x_axis_bounds,
            {"col_min": 0, "col_max": 0, "row_min": 0, "row_max": 0},
        )
        self.assertIsInstance(result.wb, Workbook)
        self.assertIsNotNone(result.ws)

    def test_insert_data(self):
        data = [
            {
                self.unit: {
                    "data": [
                        ["052297777", None, None],
                        ["ACP169 BU_FZ156", None, None],
                        ["row_numb", "date_time", "celsius"],
                        [1, datetime.datetime(2020, 3, 16, 10, 30), 0.0],
                        [2, datetime.datetime(2020, 3, 16, 10, 40), 0.5],
                        [3, datetime.datetime(2020, 3, 16, 10, 50), 1.0],
                        [4, datetime.datetime(2020, 3, 16, 11, 00), 1.5],
                        [5, datetime.datetime(2020, 3, 16, 11, 10), 2.0],
                    ],
                    "data_row_min": 3,
                    "data_row_max": 7,
                    "data_width": 3,
                }
            }
        ]
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        output_path = "unused_path"
        output_dir = Path("output")
        xlsxgraph = XLSXGraph(data, output_dir, output_path)
        xlsxgraph.insert_data()
        self.assertEqual(
            xlsxgraph.x_axis_bounds,
            {"col_min": 10, "col_max": 10, "row_min": 3, "row_max": 7},
        )
        (data,) = xlsxgraph.data_to_graph
        self.assertEqual(
            data[self.unit]["y_axis_bounds"],
            {"col_min": 12, "col_max": 12, "row_min": 3, "row_max": 7},
        )
        self.assertEqual(xlsxgraph.start_col, 14)

    def test_insert_chart(self):
        data = [
            {
                self.unit: {
                    "data": [
                        ["052297777", None, None],
                        ["ACP169 BU_FZ156", None, None],
                        ["row_numb", "date_time", "celsius"],
                        [1, datetime.datetime(2020, 3, 16, 10, 30), 0.0],
                        [2, datetime.datetime(2020, 3, 16, 10, 40), 0.5],
                        [3, datetime.datetime(2020, 3, 16, 10, 50), 1.0],
                        [4, datetime.datetime(2020, 3, 16, 11, 00), 1.5],
                        [5, datetime.datetime(2020, 3, 16, 11, 10), 2.0],
                    ],
                    "data_row_min": 3,
                    "data_row_max": 7,
                    "data_width": 3,
                }
            }
        ]
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        output_path = f"{today}_unittests_graph"
        output_dir = Path("output")
        xlsxgraph = XLSXGraph(data, output_dir, output_path)
        xlsxgraph.insert_data()
        xlsxgraph.insert_chart()


if __name__ == "__main__":
    unittest.main()
