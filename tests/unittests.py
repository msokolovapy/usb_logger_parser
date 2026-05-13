import unittest
from unittest.mock import Mock
from unittest.mock import patch
import pandas as pd
from pandas import Timestamp
from src.usb_logger_parser.app import logger
from src.usb_logger_parser.storage_units import (
    StorageCondition,
    Fridge,
    create_storage_condition_manually,
)
from src.usb_logger_parser.helper_functions import (
    read,
    parse_,
    get_user_confirmation,
    validate_,
    get_average_temp,
    get_extreme_date_time,
    get_extreme_temp,
    get_spike_duration,
)
from src.usb_logger_parser.analytical_service import AnalyticalService

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
        self.file_basename = "ACPL234_ACPL01_09Apr2026"

    def tearDown(self):
        pass

    @patch("src.usb_logger_parser.storage_units.create_storage_condition_manually")
    @patch("src.usb_logger_parser.storage_units.get_user_confirmation")
    @patch("src.usb_logger_parser.storage_units.get_average_temp")
    @patch("src.usb_logger_parser.storage_units.read")
    def test_create_cc_unit(
        self, mock_read, mock_get_ave_temp, mock_user_confirmation, mock_manual_create
    ):
        file = "dummy.txt"
        mock_read.return_value = (
            self.df_temp_data,
            self.logger_id,
            self.serial_numb,
            self.file_basename,
        )
        mock_get_ave_temp.return_value = 5.0
        mock_user_confirmation.side_effect = ["abracadabra", "FG"]
        mock_manual_create.return_value = Fridge(
            self.df_temp_data, self.logger_id, self.serial_numb, self.file_basename
        )

        fridge = StorageCondition.create_from_(file)
        self.assertIsNotNone(fridge)
        self.assertEqual(fridge.low_alarm, 2.0)
        self.assertEqual(fridge.high_alarm, 8.0)
        self.assertEqual(fridge.spike_duration, 3600)
        self.assertEqual(fridge.logger.id, "ACPL01")
        self.assertEqual(fridge.logger.serial_numb, "00001")
        self.assertEqual(fridge.temp_data.shape, (20, 6))
        self.assertEqual(fridge.metadata, "ACPL234_ACPL01_09Apr2026")


class TestHelperFunctions(unittest.TestCase):
    def setUp(self):
        self.df_temp_data = SAMPLE_DF
        self.logger_id = "ACPL01"
        self.serial_numb = "00000001"
        self.file_basename = "ACPL234_ACPL01_09Apr2026"

    def tearDown(self):
        pass

    @patch("builtins.input")
    def test_create_storage_condition_manually(self, mock_input):
        mock_input.side_effect = ["abracadabra", "FG"]
        storage_condit = create_storage_condition_manually(
            self.df_temp_data, self.logger_id, self.serial_numb, self.file_basename
        )
        self.assertIsNotNone(storage_condit)
        self.assertEqual(storage_condit.high_alert, 15.0)

    def test_get_average_temp(self):
        df = pd.DataFrame({"celsius": [-25.0, -26.0, -24.0, -23.0]})
        average_temp = get_average_temp(df)
        self.assertEqual(average_temp, -24.5)

    @patch("os.path.basename")
    @patch(f"{__name__}.validate_")
    @patch(f"{__name__}.pd.read_csv")
    def test_read(self, mock_read_csv, mock_valid_data, mock_basename):
        mock_valid_data.return_value = "dummy.txt"
        mock_read_csv.return_value = pd.DataFrame(self.df_temp_data)
        mock_basename.return_value = self.file_basename
        expected_column_names = ["date_time", "celsius", "high_alarm", "low_alarm"]

        df_temp_data, logger_id, serial_numb, file_basename = read("dummy.txt")

        self.assertEqual(logger_id, "ACP169 BU_FZ156")
        self.assertEqual(serial_numb, "052297777")
        self.assertEqual(list(df_temp_data.columns), expected_column_names)

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


class TestAnalyticalServiceInit(unittest.TestCase):
    def test_analyt_service_init(self):
        analytical_service = AnalyticalService()
        self.assertIsNotNone(analytical_service.analyze_spikes)


class TestAnalyzeSpikes(unittest.TestCase):
    def setUp(self):
        self.analytical_service = AnalyticalService()
        self.unit = Fridge(*parse_(SAMPLE_DF), "dummy_txt")

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
            patch.object(AnalyticalService, "annotate_spike_dict_with_metadata") as mock_annotate_dict,
        ):
            mock_add_status.side_effect = ["df_added_status"]
            mock_cumulat_id.side_effect = ["df_with_cumulat_spike_id"]
            mock_last_spike.side_effect = ["df_last_spike_added"]
            mock_extremes.side_effect = ["df_extremes"]
            mock_excursions_df.side_effect = ["df_excursions"]
            mock_renumber_spikes.return_value = "df_renumbered_spikes"
            mock_check_limits.return_value = "df_checked_against_limits"
            mock_mkt.return_value = "spike_dict_mkt_calculated"
            mock_annotate_dict.return_value = 'spike_dict_annotated'

            result = self.analytical_service.analyze_spikes([self.unit])

            pd.testing.assert_frame_equal(mock_add_status.call_args[0][0], self.unit.temp_data)
            self.assertEqual(mock_add_status.call_args[0][1], 2.0)
            self.assertEqual(mock_add_status.call_args[0][2], 8.0)


            mock_cumulat_id.assert_called_with("df_added_status")
            mock_last_spike.assert_called_with("df_with_cumulat_spike_id")
            mock_extremes.assert_called_with("df_with_cumulat_spike_id")
            mock_excursions_df.assert_called_with("df_last_spike_added", "df_extremes")
            mock_renumber_spikes.assert_called_with("df_excursions")
            mock_check_limits.assert_called_with(

                "df_renumbered_spikes", self.unit.spike_duration, self.unit.total_spikes_duration
            )
            mock_mkt.assert_called_with(
                "df_checked_against_limits", self.unit.temp_data
            )
            mock_annotate_dict.assert_called_with('spike_dict_mkt_calculated', 'ACP169 BU_FZ156', '052297777', 'dummy_txt')

            self.assertEqual(result, ["spike_dict_annotated"])
        
        spike_dict = self.analytical_service.analyze_spikes([self.unit])
        self.fail('finish testing')

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

    def test_annotate_spike_dict_with_metadata(self):
        spike_dict = {}
        result = self.analytical_service.annotate_spike_dict_with_metadata(
            spike_dict,
            self.unit.logger.id,
            self.unit.logger.serial_numb,
            self.unit.metadata,
        )
        self.assertEqual(result["logger_id"], "ACP169 BU_FZ156")
        self.assertEqual(result["logger_serial_number"], "052297777")
        self.assertEqual(result["file_name"], "dummy_txt")


if __name__ == "__main__":
    unittest.main()
