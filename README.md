# DQChecker

DQChecker is a simple Python data quality checker for CSV files and Pandas DataFrames.
It can run as a library or as a local Flask web app.

## Install

```powershell
pip install -r requirements.txt
```

## Run the web app

```powershell
python -m src.app
```

Open `http://localhost:5000` in your browser.

## Use as a library

```python
import pandas as pd
from src.dq_checker import run_full_report

df = pd.read_csv("your_data.csv")
report = run_full_report(df, source="your_data.csv", key_col="id")
print(report.summary())
```

## Project structure

```
DQChecker/
+-- dq_checker.py
+-- requirements.txt
+-- src/
�   +-- app.py
+-- README.md
```

## Notes

- `src/app.py` contains the Flask web app.
- `dq_checker.py` contains the core quality checks.
- This repo is ready to run locally with Python.
