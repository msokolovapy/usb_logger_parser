# 🌡️ USB Data Logger Parser

> *Parse Lascar USB Temperature Data Logger EL-USB-1 CSV files, detect excursions, and generate summary reports.*

## 🌟 Highlights

- Parses CSV files exported from Lascar USB Temperature Data Logger (EL-USB-1)
- Detects excursions against configurable upper/lower temperature limits
- Calculates individual and total excursion duration (using rolling 24-hour window)
- Calculates Mean Kinetic Temperature (MKT) for failing excursions (using 12-hr before and after window)
- Saves excursions dictionary as .xlsx file
- Overlays and graphs temperature data. Saves as .xlsx file.
- Vectorised `pandas` operations for performance
- Class-based structure for maintainability

## ℹ️ Overview

USB Data Logger Parser is a Python pipeline for processing cold chain temperature data. It reads CSV files from USB loggers, identifies periods where temperature falls outside defined limits, and characterises each excursion by duration, extreme temperature and extreme date/time. If an excursion is outside a specified limit, MKT is calculated. Temperature data and excursions dictionary may be reported as .xlsx files.

The tool is designed for batch processing — useful wherever you need a reliable, repeatable way to review temperature records and flag potential compliance issues.

## 🚀 Usage

```python
from usb_logger_parser.analytical_service import AnalyticalService
from usb_logger_parser.reporting_service import ReportingService
from usb_logger_parser.storage_units import StorageCondition

file_list = []
reporting_service = ReportingService()
analytical_service = AnalyticalService()
storage_units = [StorageCondition.create_from_(file) for file in files]
spike_dicts = analytical_service.analyze_spikes(storage_units)
xlsx_spike_report = reporting_service.report_spike_dict_(spike_dicts)
xlsx_data_report = reporting_service.report_data_(storage_units)
```

## ⬇️ Installation

Requires Python 3.x and `pandas`.

```bash
pip install -e .
```

Dependencies are declared in `usb_logger_parser.toml`.

## ⚙️ Configuration

Predefined limit profiles are available for common storage conditions 
(`fridge`, `freezer`, `cold_storage`, `storage_25c`, `storage_50c`). 
Custom profiles can be defined using `LimitValues`. Defaults reflect typical cold chain requirements — adjust to match your product's storage conditions.

## 📁 Project Structure

```
usb_logger_parser/
├── README.md
├── LICENSE
├── pyproject.toml
├── usb_logger_parser/
│   ├── __init__.py
│   ├── app.py     
│   └── helper_functions.py
│   └── storage_units.py
│   └── analytical_service.py
│   └── reporting_service.py
│   
└── tests/
    └── unittests.py

## 📝 Notes

- CSV format is specific to the USB loggers in use; other logger formats may require adapter logic.
- The pipeline is designed for batch processing of multiple logger files.
- Active development branch: `usb_logger_parser_refactor`.

## 📄 License

GPL-3.0-or-later