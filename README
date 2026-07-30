# 🌡️ USB Data Logger Parser

> *Parse Lascar USB Temperature Data Logger EL-USB-1 files, detect excursions, and generate summary reports.*

## 🌟 Highlights

- Parses files exported from Lascar USB Temperature Data Logger (EL-USB-1)
- Detects excursions against configurable upper/lower temperature limits
- Calculates individual and total excursion duration (using rolling 24-hour window)
- Calculates Mean Kinetic Temperature (MKT) for failing excursions (using 12-hr before and after window)
- Saves excursions dictionary as .xlsx file
- Overlays and graphs temperature data. Saves as .xlsx file.
- Vectorised `pandas` operations for performance
- Class-based structure for maintainability

## ℹ️ Overview

USB Data Logger Parser is a Python pipeline for processing cold chain temperature data. It reads files from Lascar ELB USB loggers, identifies periods where temperature falls outside defined limits, and characterises each excursion by duration, extreme temperature and extreme date/time. If an excursion is outside a specified limit, MKT is calculated. Temperature data and excursions dictionary may be reported as .xlsx files.

The tool is designed for batch processing.

## 🚀 Usage

```python
from usb_logger_parser.analytical_service import AnalyticalService
from usb_logger_parser.reporting_service import ReportingService
from usb_logger_parser.storage_units import StorageCondition
from usb_logger_parser.helper_functions import get_files

file_list = get_files('usb_logger_parser', 'resources')
reporting_service = ReportingService()
analytical_service = AnalyticalService()
storage_units = [StorageCondition.create_from_(file) for file in file_list]
temp_spikes = analytical_service.analyze_spikes(storage_units)
reporting_service.report_spikes(temp_spikes)
reporting_service.report_raw_data(storage_units)
```

## ⬇️ Installation

Requires Python 3.9+.

```bash
pip install -e .
```

## ⚙️ Configuration

Predefined limit profiles are available for common storage conditions
(`fridge`, `freezer`, `cold_storage`, `storage_25c`, `storage_50c`).
Custom profiles can be defined using `LimitValues`. Defaults reflect typical cold chain requirements — adjust to match your product's storage conditions.

## 📁 Project Structure

```
src/
└── usb_logger_parser/
    ├── resources/
    │   ├── ACP169_30-03-2020_artificial_spikes.txt
    │   └── ACPL211 in ACPL229 20.5.22 to 3.8.22.txt
    ├── __init__.py
    ├── app.py
    ├── helper_functions.py
    ├── storage_units.py
    ├── analytical_service.py
    └── reporting_service.py

tests/
├── unittests.py
└── integration_tests.py

README.md
LICENSE
pyproject.toml
```

## 📝 Notes

- File format is specific to the USB loggers in use; other logger formats may require adapter logic.
- The pipeline is designed for batch processing of multiple logger files.

## 📄 License

GPL-3.0-or-later