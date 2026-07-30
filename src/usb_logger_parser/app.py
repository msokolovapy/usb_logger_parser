import logging
from analytical_service import AnalyticalService
from reporting_service import ReportingService
from storage_units import StorageCondition
from helper_functions import get_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log")],
)


def main():
    file_list = get_files('usb_logger_parser', 'resources')
    reporting_service = ReportingService()
    analytical_service = AnalyticalService()
    storage_units = [StorageCondition.create_from_(file) for file in file_list]
    temp_spikes = analytical_service.analyze_spikes(storage_units)
    reporting_service.report_spikes(temp_spikes)
    reporting_service.report_raw_data(storage_units)


if __name__ == "__main__":
    main()
