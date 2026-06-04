
<div align="center">

# 🔍 DQChecker

### A data quality checker for engineers who are tired of broken pipelines.

**Use it as a Python library inside your pipeline · or as a web app — no code needed.**


</div>

## 🤔 What is DQChecker?

DQChecker is a free, open-source **data quality tool** built in Python. It inspects any CSV file or Pandas DataFrame and produces a structured report covering the four most common data quality issues:

- **Null values** — which columns have missing data, and how much
- **Duplicates** — duplicate rows and primary key violations
- **Outliers** — numeric values that fall outside expected ranges
- **Schema issues** — constant columns, high-null columns, and type information

It returns an **overall quality score out of 100** so you always know at a glance whether your data is safe to process.

---

## 🚑 Why does this matter?

Most pipeline failures don't come from broken code. They come from bad data.

In 4+ years of building data pipelines across healthcare analytics and enterprise BI, the same issues kept causing the same downstream failures:

- A null `diagnosis_code` silently breaks a JOIN and produces missing rows in the report
- A duplicate `patient_id` inflates record counts by 8% — no error thrown
- An outlier age of `999` skews the average age cohort calculation for an entire dashboard

These problems are **invisible until they reach production**. DQChecker catches them at the source — before your pipeline runs, before your dashboard lies, before your stakeholder asks why the numbers look wrong.

```
Without DQChecker:  raw CSV → pipeline → broken dashboard → manual debug → fix → re-run
With DQChecker:     raw CSV → lint → fix → pipeline → clean dashboard ✓
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Core library | Python 3.8+, Pandas, NumPy |
| Web app | Flask 2.3+ |
| Frontend | Vanilla HTML/CSS/JS (single file, zero dependencies) |
| Outlier detection | IQR (interquartile range) and Z-score |
| Output formats | Text summary, JSON, Python dataclass |

No database. No cloud dependency. Runs entirely on your machine.

---

## ⚡ Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/aindriladutta25/DQChecker
cd DQChecker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

That's it. Two files matter:

| File | What it is |
|---|---|
| `dq_checker.py` | Standalone Python library — use this in your pipeline |
| `app.py` | Flask web app — drag-and-drop UI for non-coders |

---

## 📦 Using `dq_checker.py` as a Library

`dq_checker.py` is a **single self-contained file**. You can copy it directly into any existing project without installing anything beyond Pandas and NumPy.

### The simplest possible usage

```python
import pandas as pd
from dq_checker import run_full_report

df = pd.read_csv("your_data.csv")
report = run_full_report(df, source="your_data.csv")
print(report.summary())
```

**Output:**
```
=======================================================
  DATA QUALITY REPORT — patients.csv
=======================================================
  Rows: 100   Columns: 6
  Overall Score: 58.3/100
───────────────────────────────────────────────────────
  NULLS          FAIL
    diagnosis: 3 nulls (3.0%)
    wait_time_mins: 2 nulls (2.0%)
    notes: 100 nulls (100.0%)
  DUPLICATES     FAIL
    5 duplicate keys in 'patient_id'
  OUTLIERS       FAIL
    age: 2 outliers (2.0%)
  SCHEMA         FAIL
    High-null cols (>50%): ['notes']
    Constant/useless cols: ['status', 'notes']
=======================================================
```

---

### One-liner from a file path

```python
from dq_checker import check_csv

# Loads the CSV, runs all checks, prints summary, returns report
report = check_csv("sales_data.csv", key_col="order_id")
```

---

### All available parameters

```python
from dq_checker import run_full_report

report = run_full_report(
    df,                          # Your Pandas DataFrame
    source="patients.csv",       # Label shown in the report (usually the filename)
    key_col="patient_id",        # Primary key column — checked for duplicates
    critical_cols=["dob",        # These columns must have zero nulls
                   "diagnosis_code"],
    outlier_method="IQR",        # "IQR" (default) or "zscore"
    null_threshold=0.5,          # Columns with >50% nulls are flagged
    print_summary=True,          # Print the text report to stdout
)
```

---

### Exporting to JSON

```python
# Perfect for logging, alerting, or feeding into a dashboard
print(report.to_json())

# Or save to disk
with open("dq_report.json", "w") as f:
    f.write(report.to_json())
```

**JSON output structure:**
```json
{
  "source": "patients.csv",
  "row_count": 100,
  "col_count": 6,
  "overall_score": 58.3,
  "nulls": {
    "has_issues": true,
    "columns": {
      "diagnosis": { "null_count": 3, "null_pct": 3.0 }
    }
  },
  "duplicates": {
    "has_issues": true,
    "duplicate_rows": 0,
    "duplicate_keys": 5,
    "key_col": "patient_id"
  },
  "outliers": { "has_issues": true, "columns": { ... } },
  "schema":   { "has_issues": true, "high_null_cols": ["notes"] }
}
```

---

### Using individual checks

You don't have to run the full report. Each check is a standalone function:

```python
from dq_checker import check_nulls, check_duplicates, check_outliers, check_schema

# Check nulls — flag specific columns as critical
nulls = check_nulls(df, critical_cols=["patient_id", "diagnosis_code"])
print(nulls.has_issues())      # True / False
print(nulls.columns)           # dict of {col: {null_count, null_pct}}

# Check duplicates
dupes = check_duplicates(df, key_col="order_id")
print(dupes.duplicate_row_count)
print(dupes.duplicate_key_count)

# Check outliers
outliers = check_outliers(df, method="IQR")   # or "zscore"
print(outliers.columns)        # dict of {col: {outlier_count, outlier_pct, lower_bound, upper_bound}}

# Check schema
schema = check_schema(df, null_threshold=0.5)
print(schema.constant_cols)    # columns with only one unique value
print(schema.high_null_cols)   # columns with >50% nulls
```

---

### 🔗 Plugging into an existing pipeline

The most powerful use case: run DQChecker as a **pre-flight gate** before your pipeline processes data. If quality is below your threshold, abort and alert.

```python
import pandas as pd
import sys
import logging
from dq_checker import run_full_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline")

def run_pipeline(filepath: str, key_col: str, min_score: int = 70):
    """
    Load data, lint it, abort if quality is too low, otherwise process.
    """
    df = pd.read_csv(filepath)

    # ── Step 1: Lint ──────────────────────────────────────
    logger.info(f"Running DQChecker on {filepath}...")
    report = run_full_report(
        df,
        source=filepath,
        key_col=key_col,
        critical_cols=["id", "date"],   # these must have zero nulls
        print_summary=True,
    )

    # ── Step 2: Quality gate ──────────────────────────────
    if report.overall_score < min_score:
        logger.error(f"Quality score {report.overall_score}/100 is below threshold {min_score}. Aborting.")
        # Save report for debugging
        with open("failed_dq_report.json", "w") as f:
            f.write(report.to_json())
        sys.exit(1)

    # ── Step 3: Continue pipeline ─────────────────────────
    logger.info(f"Quality check passed ({report.overall_score}/100). Proceeding.")
    df_clean = df.dropna(subset=["id", "date"])
    df_clean = df_clean.drop_duplicates(subset=[key_col])
    # ... your transformation logic here
    return df_clean


if __name__ == "__main__":
    df_ready = run_pipeline("raw_sales.csv", key_col="order_id", min_score=75)
    print(f"Pipeline complete. {len(df_ready)} clean rows ready.")
```

---

### 🏥 Real-world example: Healthcare ETL (ADF + Databricks)

This is how a version of this pattern was used in a clinical operations platform to validate EMR data before ingestion into Azure Data Lake:

```python
# pyspark_dq_gate.py — runs as a Databricks notebook cell
import pandas as pd
from dq_checker import run_full_report

# Read from ADLS staging layer (Bronze)
df = spark.read.parquet("abfss://bronze@datalake.dfs.core.windows.net/encounters/") \
          .toPandas()

report = run_full_report(
    df,
    source="encounters_bronze",
    key_col="encounter_id",
    critical_cols=["patient_id", "diagnosis_code", "encounter_date"],
    outlier_method="IQR",
)

# Write report to Silver layer for audit trail
report_df = pd.DataFrame([report.to_dict()])
spark.createDataFrame(report_df) \
     .write.mode("append") \
     .parquet("abfss://silver@datalake.dfs.core.windows.net/dq_reports/")

# Gate: only promote to Silver if score >= 80
assert report.overall_score >= 80, f"DQ gate failed: {report.overall_score}/100\n{report.summary()}"
```

---

### 💻 CLI usage

Run directly from the terminal — no Python code needed:

```bash
# Basic usage
python dq_checker.py mydata.csv

# With a primary key column
python dq_checker.py patients.csv patient_id
```

Prints the full text summary and saves a `mydata_dq_report.json` file alongside the CSV.

---

## 🌐 DQChecker Web App

The web app is for anyone who wants to check data quality **without writing any code** — analysts, ops teams, QA testers, or anyone handed a CSV they don't trust.

### Running locally

```bash
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000] in your browser.

### How to use it

1. **Drag and drop** any CSV onto the upload zone (or click to browse)
2. Optionally enter a **primary key column** name (e.g. `order_id`, `patient_id`)
3. Choose your **outlier detection method** — IQR (default) or Z-score
4. Click **Run quality check**
5. Review the scored report — expand each section for details

### What the app shows

| Section | What you see |
|---|---|
| Score circle | Overall quality score 0–100, colour-coded green/amber/red |
| Nulls | Per-column null count and percentage with a visual bar |
| Duplicates | Duplicate row count, duplicate key count, duplicate rate |
| Outliers | Per-column outlier count, percentage, and acceptable range |
| Schema | Column types, flagged constant columns, flagged high-null columns |

### App screenshot

> *[Replace this with a screenshot of your DQChecker app — drag-and-drop the image into the GitHub editor]*

---

## 📊 How the Quality Score is Calculated

The score is a weighted sum across four dimensions:

| Dimension | Weight | Penalty logic |
|---|---|---|
| Nulls | 40 pts | Penalises proportionally to total null cells across the dataset |
| Duplicates | 30 pts | Penalises proportionally to duplicate row percentage |
| Outliers | 20 pts | Based on average outlier % across all numeric columns |
| Schema | 10 pts | 2 points deducted per high-null or constant column |

| Score | Grade |
|---|---|
| 90–100 | ✅ Excellent |
| 75–89 | 🟡 Good |
| 50–74 | 🟠 Needs attention |
| 0–49 | 🔴 Poor quality |

---

## 📁 Project Structure

```
DQChecker/
├── dq_checker.py       ← Standalone library (copy this into any project)
├── app.py              ← Flask web app
├── requirements.txt    ← Dependencies
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome. Ideas for extensions:

- Support for Excel (`.xlsx`) and JSON files
- Email/Slack alerts when quality drops below a threshold
- Scheduled checks with a cron runner
- Great Expectations integration
- Export report as a PDF

Fork the repo, make your changes, and open a PR.

---

## 👩‍💻 Author

**Aindrila Dutta** — Data Engineer  
4+ years building data pipelines in healthcare analytics and enterprise BI.  
Azure · Databricks · Power BI · Python · SQL

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/aindrila-dutta25)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?style=flat-square&logo=github)](https://github.com/aindriladutta25)

---

## 📄 License

MIT — free to use, modify, and distribute.

---

<div align="center">
If DQChecker saved you time, consider giving the repo a ⭐ — it helps other engineers find it.
</div>