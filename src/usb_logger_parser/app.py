from src.usb_logger_parser.analytical_service import AnalyticalService
from src.usb_logger_parser.reporting_service import ReportingService


def main():
	file_list = []
	reporting_service = ReportingService()
	analytical_service = AnalyticalService()
	storage_units = [StorageCondition.create_from_(file) for file in files]
	spike_dicts = analytical_service.analyze_spikes(storage_units)
	xlsx_spike_reports = reporting_service.report_spike_dict_(spike_dicts)
	xlsx_data_reports = reporting_service.report_data_(storage_units)