from dataclasses import dataclass
from src.usb_logger_parser.helper_functions import (
    read,
    get_average_temp,
    get_user_confirmation,
    get_ave_data_coll_freq,
)


class StorageCondition:
    @classmethod
    def create_from_(cls, file):
        df_temp_data, logger_id, serial_numb, file_basename = read(file)
        average_temp = get_average_temp(df_temp_data)
        ave_data_coll_freq = get_ave_data_coll_freq(df_temp_data)
        if (
            Limits.cold_storage.low_alarm
            <= average_temp
            <= Limits.cold_storage.high_alarm
        ):
            while True:
                user_input = get_user_confirmation()
                if user_input == "FG":
                    return Fridge(
                        df_temp_data,
                        logger_id,
                        serial_numb,
                        ave_data_coll_freq,
                        file_basename,
                    )
                elif user_input == "CS":
                    return ColdStorage(
                        df_temp_data,
                        logger_id,
                        serial_numb,
                        ave_data_coll_freq,
                        file_basename,
                    )
                else:
                    print("Please either enter FG or CS")
                    continue
        elif (
            Limits.freezer.low_alarm
            <= average_temp
            <= Limits.freezer.high_alarm
        ):
            return Freezer(
                df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
            )
        elif (
            Limits.storage_25c.low_alarm
            <= average_temp
            <= Limits.storage_25c.high_alarm
        ):
            return TwentyFiveCelsius(
                df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
            )
        elif (
            Limits.storage_50c.low_alarm
            <= average_temp
            <= Limits.storage_50c.high_alarm
        ):
            return FiftyCelsius(
                df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
            )
        else:
            return create_storage_condition_manually(
                df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
            )


def create_storage_condition_manually(
    df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
):
    storage_condit_dict = {
        "FG": Fridge(
            df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
        ),
        "FZ": Freezer(
            df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
        ),
        "CS": ColdStorage(
            df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
        ),
        "25C": TwentyFiveCelsius(
            df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
        ),
        "50C": FiftyCelsius(
            df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
        ),
    }
    while True:
        user_input = input(
            "Storage condition not clear. Please clarify storage condition for your temperature trace '{file_basename}' for logger {logger_id} here (FG/FZ/CS/25C/50C):"
        )
        if user_input in storage_condit_dict.keys():
            storage_condition = storage_condit_dict[user_input]
            return storage_condition
        else:
            storage_str = ("/ ").join(storage_condit_dict.keys())
            print(f"Please select storage condition from {storage_str}")
            continue


class Fridge:
    def __init__(
        self, df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
    ):
        self.low_alarm = Limits.fridge.low_alarm
        self.high_alarm = Limits.fridge.high_alarm
        self.low_alert = Limits.fridge.low_alert
        self.high_alert = Limits.fridge.high_alert
        self.spike_duration = Limits.fridge.spike_duration
        self.total_spikes_duration = Limits.fridge.total_spikes_duration
        self.temp_data = df_temp_data
        self.logger = USBLogger(
            id=logger_id, serial_numb=serial_numb, ave_data_coll_freq=ave_data_coll_freq
        )
        self.file_basename = file_basename

    @property
    def metadata(self):
        return [
            ["usb_logger_id", self.logger.id],
            ["usb_logger_serial_number", self.logger.serial_numb],
            ["file_name", self.file_basename],
        ]


class Freezer:
    def __init__(
        self, df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
    ):
        self.low_alarm = Limits.freezer.low_alarm
        self.high_alarm = Limits.freezer.high_alarm
        self.low_alert = Limits.freezer.low_alert
        self.high_alert = Limits.freezer.high_alert
        self.spike_duration = Limits.freezer.spike_duration
        self.total_spikes_duration = Limits.freezer.total_spikes_duration
        self.temp_data = df_temp_data
        self.logger = USBLogger(
            id=logger_id, serial_numb=serial_numb, ave_data_coll_freq=ave_data_coll_freq
        )
        self.file_basename = file_basename

    @property
    def metadata(self):
        return [
            ["usb_logger_id", self.logger.id],
            ["usb_logger_serial_number", self.logger.serial_numb],
            ["file_name", self.file_basename],
        ]


class ColdStorage:
    def __init__(
        self, df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
    ):
        self.low_alarm = Limits.cold_storage.low_alarm
        self.high_alarm = Limits.cold_storage.high_alarm
        self.low_alert = Limits.cold_storage.low_alert
        self.high_alert = Limits.cold_storage.high_alert
        self.spike_duration = Limits.cold_storage.spike_duration
        self.total_spikes_duration = Limits.cold_storage.total_spikes_duration
        self.temp_data = df_temp_data
        self.logger = USBLogger(
            id=logger_id, serial_numb=serial_numb, ave_data_coll_freq=ave_data_coll_freq
        )
        self.file_basename = file_basename

    @property
    def metadata(self):
        return [
            ["usb_logger_id", self.logger.id],
            ["usb_logger_serial_number", self.logger.serial_numb],
            ["file_name", self.file_basename],
        ]


class TwentyFiveCelsius:
    def __init__(
        self, df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
    ):
        self.low_alarm = Limits.storage_25c.low_alarm
        self.high_alarm = Limits.storage_25c.high_alarm
        self.low_alert = Limits.storage_25c.low_alert
        self.high_alert = Limits.storage_25c.high_alert
        self.spike_duration = Limits.storage_25c.spike_duration
        self.total_spikes_duration = Limits.storage_25c.total_spikes_duration
        self.temp_data = df_temp_data
        self.logger = USBLogger(
            id=logger_id, serial_numb=serial_numb, ave_data_coll_freq=ave_data_coll_freq
        )
        self.file_basename = file_basename

    @property
    def metadata(self):
        return [
            ["usb_logger_id", self.logger.id],
            ["usb_logger_serial_number", self.logger.serial_numb],
            ["file_name", self.file_basename],
        ]


class FiftyCelsius:
    def __init__(
        self, df_temp_data, logger_id, serial_numb, ave_data_coll_freq, file_basename
    ):
        self.low_alarm = Limits.storage_50c.low_alarm
        self.high_alarm = Limits.storage_50c.high_alarm
        self.low_alert = Limits.storage_50c.low_alert
        self.high_alert = Limits.storage_50c.high_alert
        self.spike_duration = Limits.storage_50c.spike_duration
        self.total_spikes_duration = Limits.storage_50c.total_spikes_duration
        self.temp_data = df_temp_data
        self.logger = USBLogger(
            id=logger_id, serial_numb=serial_numb, ave_data_coll_freq=ave_data_coll_freq
        )
        self.file_basename = file_basename

    @property
    def metadata(self):
        return [
            ["usb_logger_id", self.logger.id],
            ["usb_logger_serial_number", self.logger.serial_numb],
            ["file_name", self.file_basename],
        ]


@dataclass
class USBLogger:
    id: str
    serial_numb: str
    ave_data_coll_freq: float


@dataclass
class LimitValues:
    low_alarm: float
    high_alarm: float
    low_alert: float
    high_alert: float
    spike_duration: int
    total_spikes_duration: int


class Limits:
    fridge = LimitValues(2.0, 8.0, 0.0, 15.0, 60, 180)
    freezer = LimitValues(-25.0, -15.0, -30.0, -0.1, 60, 180)
    cold_storage = LimitValues(-10.0, 10.0, -20.0, 20.0, 60, 180)
    storage_25c = LimitValues(24.0, 26.0, 15.0, 30.0, 15, 180)
    storage_50c = LimitValues(45.0, 55.0, 25.0, 60.0, 15, 180)
