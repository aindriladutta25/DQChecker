# Data Quality Checker

DataLint is a reusable Data Quality Checker designed to help you ensure the integrity and quality of your datasets. This project provides a set of tools to check for null values, duplicates, outliers, and schema issues in your data.

## Features

- **Null Checks**: Identify columns with null values and assess their impact on your dataset.
- **Duplicate Checks**: Detect duplicate rows and unique key violations.
- **Outlier Detection**: Find outliers in numeric columns using various methods.
- **Schema Validation**: Inspect column types, high-null columns, and constant/useless columns.

## Installation

To install the required dependencies, run:

```
pip install -r requirements.txt
```

## Usage

You can use the Data Quality Checker in your projects by importing the necessary functions from the `dq_checker` module. Here’s a quick example:

```python
import pandas as pd
from dq_checker import run_full_report

# Load your DataFrame
df = pd.read_csv("your_data.csv")

# Run the data quality report
report = run_full_report(df, source="your_data.csv", key_col="id", critical_cols=["column1", "column2"])

# Print the summary
print(report.summary())
```

## Web App

The Flask web app in `app.py` uploads CSV files to a temporary file and then reads it with `pd.read_csv()` after the temp file has been closed. The temp file is removed in a `finally` block, so it is cleaned up even if reading fails.

To run the web app:

```powershell
python DataLint/app.py
```

Then open `http://localhost:5000` in your browser.

## Testing

To ensure the functionality of the Data Quality Checker, unit tests are provided in the `tests` directory. You can run the tests using:

```
pytest tests/test_dq_checker.py
```

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.