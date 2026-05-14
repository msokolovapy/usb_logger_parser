import logging
from analytical_service import AnalyticalService
from reporting_service import ReportingService
from storage_units import StorageCondition

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)


def main():
    file_list = []
    reporting_service = ReportingService()
    analytical_service = AnalyticalService()
    storage_units = [StorageCondition.create_from_(file) for file in file_list]
    spike_dicts = analytical_service.analyze_spikes(storage_units)
    xlsx_spike_reports = reporting_service.report_spike_dict_(spike_dicts)
    xlsx_data_reports = reporting_service.report_data_(storage_units)


if __name__ == "__main__":
    main()
