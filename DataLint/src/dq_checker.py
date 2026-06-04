"""
dq_checker.py : Reusable Data Quality Checker
Author: Aindrila Dutta | github.com/aindrila-dutta
------------------------------------------------------
Drop this file into any project and import the functions
you need. Works standalone or as part of a pipeline.

Usage:
    from dq_checker import run_full_report, check_nulls, check_duplicates
    report = run_full_report(df, key_col="patient_id")
    print(report.summary())
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import json
import warnings

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
# Data classes for structured results
# ─────────────────────────────────────────────

@dataclass
class NullReport:
    total_rows: int
    columns: dict          # {col: {"null_count": int, "null_pct": float}}
    critical_cols_failed: list

    def has_issues(self) -> bool:
        return any(v["null_count"] > 0 for v in self.columns.values())


@dataclass
class DuplicateReport:
    total_rows: int
    duplicate_row_count: int
    duplicate_key_count: int
    key_col: Optional[str]
    duplicate_pct: float

    def has_issues(self) -> bool:
        return self.duplicate_row_count > 0 or self.duplicate_key_count > 0


@dataclass
class OutlierReport:
    columns: dict          # {col: {"outlier_count": int, "outlier_pct": float, "lower": float, "upper": float}}
    method: str = "IQR"

    def has_issues(self) -> bool:
        return any(v["outlier_count"] > 0 for v in self.columns.values())


@dataclass
class SchemaReport:
    total_rows: int
    total_cols: int
    dtypes: dict                 # {col: dtype_string}
    low_cardinality_cols: list   # likely categorical stored as object
    high_null_cols: list         # > 50% null
    constant_cols: list          # single unique value — useless columns

    def has_issues(self) -> bool:
        return bool(self.high_null_cols or self.constant_cols)


@dataclass
class DataQualityReport:
    source: str
    row_count: int
    col_count: int
    nulls: NullReport
    duplicates: DuplicateReport
    outliers: OutlierReport
    schema: SchemaReport
    overall_score: float = 0.0  # 0–100

    def summary(self) -> str:
        lines = [
            f"\n{'='*55}",
            f"  DATA QUALITY REPORT — {self.source}",
            f"{'='*55}",
            f"  Rows: {self.row_count:,}   Columns: {self.col_count}",
            f"  Overall Score: {self.overall_score:.1f}/100",
            f"{'─'*55}",
            f"  NULLS          {'FAIL' if self.nulls.has_issues() else 'PASS'}",
        ]
        for col, info in self.nulls.columns.items():
            if info["null_count"] > 0:
                lines.append(f"    {col}: {info['null_count']} nulls ({info['null_pct']:.1f}%)")

        lines.append(f"  DUPLICATES     {'FAIL' if self.duplicates.has_issues() else 'PASS'}")
        if self.duplicates.duplicate_row_count > 0:
            lines.append(f"    {self.duplicates.duplicate_row_count} duplicate rows ({self.duplicates.duplicate_pct:.1f}%)")
        if self.duplicates.duplicate_key_count > 0:
            lines.append(f"    {self.duplicates.duplicate_key_count} duplicate keys in '{self.duplicates.key_col}'")

        lines.append(f"  OUTLIERS       {'FAIL' if self.outliers.has_issues() else 'PASS'}")
        for col, info in self.outliers.columns.items():
            if info["outlier_count"] > 0:
                lines.append(f"    {col}: {info['outlier_count']} outliers ({info['outlier_pct']:.1f}%)")

        lines.append(f"  SCHEMA         {'FAIL' if self.schema.has_issues() else 'PASS'}")
        if self.schema.high_null_cols:
            lines.append(f"    High-null cols (>50%): {self.schema.high_null_cols}")
        if self.schema.constant_cols:
            lines.append(f"    Constant/useless cols: {self.schema.constant_cols}")

        lines.append(f"{'='*55}\n")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "row_count": self.row_count,
            "col_count": self.col_count,
            "overall_score": round(self.overall_score, 1),
            "nulls": {
                "has_issues": self.nulls.has_issues(),
                "columns": self.nulls.columns,
                "critical_failed": self.nulls.critical_cols_failed,
            },
            "duplicates": {
                "has_issues": self.duplicates.has_issues(),
                "duplicate_rows": self.duplicates.duplicate_row_count,
                "duplicate_keys": self.duplicates.duplicate_key_count,
                "key_col": self.duplicates.key_col,
                "duplicate_pct": round(self.duplicates.duplicate_pct, 2),
            },
            "outliers": {
                "has_issues": self.outliers.has_issues(),
                "columns": self.outliers.columns,
            },
            "schema": {
                "has_issues": self.schema.has_issues(),
                "dtypes": self.schema.dtypes,
                "high_null_cols": self.schema.high_null_cols,
                "constant_cols": self.schema.constant_cols,
                "low_cardinality_cols": self.schema.low_cardinality_cols,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ─────────────────────────────────────────────
# Individual check functions (use standalone)
# ─────────────────────────────────────────────

def check_nulls(df: pd.DataFrame, critical_cols: Optional[list] = None) -> NullReport:
    """
    Check every column for null values.
    critical_cols: list of columns that must have zero nulls.
    """
    critical_cols = critical_cols or []
    col_info = {}

    for col in df.columns:
        n = int(df[col].isnull().sum())
        pct = round((n / len(df)) * 100, 2) if len(df) > 0 else 0.0
        col_info[col] = {"null_count": n, "null_pct": pct}

    failed_critical = [c for c in critical_cols if col_info.get(c, {}).get("null_count", 0) > 0]

    return NullReport(
        total_rows=len(df),
        columns=col_info,
        critical_cols_failed=failed_critical,
    )


def check_duplicates(df: pd.DataFrame, key_col: Optional[str] = None) -> DuplicateReport:
    """
    Check for duplicate rows and (optionally) duplicate values in a key column.
    key_col: primary key column that should be unique.
    """
    dup_rows = int(df.duplicated().sum())
    dup_pct = round((dup_rows / len(df)) * 100, 2) if len(df) > 0 else 0.0

    dup_keys = 0
    if key_col and key_col in df.columns:
        dup_keys = int(df[key_col].duplicated().sum())

    return DuplicateReport(
        total_rows=len(df),
        duplicate_row_count=dup_rows,
        duplicate_key_count=dup_keys,
        key_col=key_col,
        duplicate_pct=dup_pct,
    )


def check_outliers(df: pd.DataFrame, method: str = "IQR") -> OutlierReport:
    """
    Detect outliers in all numeric columns.
    method: 'IQR' (default) or 'zscore'
    """
    numeric_df = df.select_dtypes(include=[np.number])
    col_info = {}

    for col in numeric_df.columns:
        series = numeric_df[col].dropna()
        if len(series) < 4:
            continue

        if method == "IQR":
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            mask = (series < lower) | (series > upper)
        elif method == "zscore":
            z = (series - series.mean()) / series.std()
            lower = series.mean() - 3 * series.std()
            upper = series.mean() + 3 * series.std()
            mask = z.abs() > 3
        else:
            raise ValueError(f"Unknown method: {method}. Use 'IQR' or 'zscore'.")

        count = int(mask.sum())
        pct = round((count / len(series)) * 100, 2)
        col_info[col] = {
            "outlier_count": count,
            "outlier_pct": pct,
            "lower_bound": round(float(lower), 4),
            "upper_bound": round(float(upper), 4),
        }

    return OutlierReport(columns=col_info, method=method)


def check_schema(df: pd.DataFrame, null_threshold: float = 0.5) -> SchemaReport:
    """
    Inspect column types, high-null columns, and constant/useless columns.
    null_threshold: fraction above which a column is flagged as high-null (default 0.5 = 50%).
    """
    dtypes = {col: str(df[col].dtype) for col in df.columns}

    high_null = [
        col for col in df.columns
        if df[col].isnull().mean() > null_threshold
    ]

    constant = [
        col for col in df.columns
        if df[col].nunique(dropna=False) <= 1
    ]

    low_cardinality = [
        col for col in df.select_dtypes(include="object").columns
        if 1 < df[col].nunique() <= 10 and col not in constant
    ]

    return SchemaReport(
        total_rows=len(df),
        total_cols=len(df.columns),
        dtypes=dtypes,
        low_cardinality_cols=low_cardinality,
        high_null_cols=high_null,
        constant_cols=constant,
    )


# ─────────────────────────────────────────────
# Score calculation
# ─────────────────────────────────────────────

def _compute_score(nulls: NullReport, dupes: DuplicateReport,
                   outliers: OutlierReport, schema: SchemaReport) -> float:
    """
    Returns a 0–100 quality score. Weighted across four dimensions.
    Null: 40pts | Duplicate: 30pts | Outlier: 20pts | Schema: 10pts
    """
    # Null score (40 pts)
    if nulls.total_rows == 0:
        null_score = 40
    else:
        total_cells = nulls.total_rows * max(len(nulls.columns), 1)
        total_nulls = sum(v["null_count"] for v in nulls.columns.values())
        null_ratio = total_nulls / total_cells
        null_score = 40 * (1 - min(null_ratio * 5, 1))  # penalises heavily

    # Duplicate score (30 pts)
    dup_ratio = dupes.duplicate_pct / 100
    dup_score = 30 * (1 - min(dup_ratio * 10, 1))

    # Outlier score (20 pts)
    if not outliers.columns:
        outlier_score = 20
    else:
        avg_outlier_pct = np.mean([v["outlier_pct"] for v in outliers.columns.values()]) / 100
        outlier_score = 20 * (1 - min(avg_outlier_pct * 5, 1))

    # Schema score (10 pts)
    schema_deductions = len(schema.high_null_cols) * 2 + len(schema.constant_cols) * 2
    schema_score = max(0, 10 - schema_deductions)

    return round(null_score + dup_score + outlier_score + schema_score, 1)


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def run_full_report(
    df: pd.DataFrame,
    source: str = "dataframe",
    key_col: Optional[str] = None,
    critical_cols: Optional[list] = None,
    outlier_method: str = "IQR",
    null_threshold: float = 0.5,
    print_summary: bool = False,
) -> DataQualityReport:
    """
    Run all checks and return a DataQualityReport.

    Parameters
    ----------
    df              : Input DataFrame
    source          : Label for the data source (e.g. filename)
    key_col         : Column that should be unique (primary key)
    critical_cols   : Columns that must have zero nulls
    outlier_method  : 'IQR' or 'zscore'
    null_threshold  : Fraction above which a column is flagged high-null
    print_summary   : If True, prints the text summary to stdout

    Returns
    -------
    DataQualityReport

    Example
    -------
    >>> import pandas as pd
    >>> from dq_checker import run_full_report
    >>> df = pd.read_csv("patients.csv")
    >>> report = run_full_report(df, source="patients.csv", key_col="patient_id",
    ...                          critical_cols=["dob", "diagnosis_code"])
    >>> print(report.summary())
    >>> print(report.to_json())
    """
    nulls = check_nulls(df, critical_cols=critical_cols)
    dupes = check_duplicates(df, key_col=key_col)
    outliers = check_outliers(df, method=outlier_method)
    schema = check_schema(df, null_threshold=null_threshold)
    score = _compute_score(nulls, dupes, outliers, schema)

    report = DataQualityReport(
        source=source,
        row_count=len(df),
        col_count=len(df.columns),
        nulls=nulls,
        duplicates=dupes,
        outliers=outliers,
        schema=schema,
        overall_score=score,
    )

    if print_summary:
        print(report.summary())

    return report


def check_csv(
    filepath: str,
    key_col: Optional[str] = None,
    critical_cols: Optional[list] = None,
    print_summary: bool = True,
) -> DataQualityReport:
    """
    Convenience wrapper — load a CSV and run a full report in one line.

    Example
    -------
    >>> from dq_checker import check_csv
    >>> report = check_csv("sales_data.csv", key_col="order_id")
    """
    df = pd.read_csv(filepath)
    filename = filepath.split("/")[-1]
    return run_full_report(
        df,
        source=filename,
        key_col=key_col,
        critical_cols=critical_cols,
        print_summary=print_summary,
    )


# ─────────────────────────────────────────────
# CLI support: python dq_checker.py myfile.csv
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python dq_checker.py <csv_file> [key_col]")
        sys.exit(1)

    filepath = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else None

    report = check_csv(filepath, key_col=key, print_summary=True)
    out_path = filepath.replace(".csv", "_dq_report.json")
    with open(out_path, "w") as f:
        f.write(report.to_json())
    print(f"JSON report saved to: {out_path}")