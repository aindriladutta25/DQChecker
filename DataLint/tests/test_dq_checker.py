import pandas as pd
import pytest
from src.dq_checker import run_full_report, check_nulls, check_duplicates, check_outliers, check_schema

# Sample DataFrame for testing
def create_sample_dataframe():
    data = {
        'patient_id': [1, 2, 3, 4, 5, 5],
        'dob': ['1990-01-01', '1991-02-02', None, '1993-03-03', '1994-04-04', '1994-04-04'],
        'diagnosis_code': ['A01', 'A02', 'A01', None, 'A03', 'A03'],
        'value': [10, 20, 30, 40, 50, 1000]  # 1000 is an outlier
    }
    return pd.DataFrame(data)

# Test for null checking
def test_check_nulls():
    df = create_sample_dataframe()
    report = check_nulls(df, critical_cols=['dob', 'diagnosis_code'])
    assert report.has_issues() == True
    assert report.columns['dob']['null_count'] == 1
    assert report.columns['diagnosis_code']['null_count'] == 1

# Test for duplicate checking
def test_check_duplicates():
    df = create_sample_dataframe()
    report = check_duplicates(df, key_col='patient_id')
    assert report.has_issues() == True
    assert report.duplicate_row_count == 1
    assert report.duplicate_key_count == 1

# Test for outlier checking
def test_check_outliers():
    df = create_sample_dataframe()
    report = check_outliers(df, method='IQR')
    assert report.has_issues() == True
    assert report.columns['value']['outlier_count'] == 1

# Test for schema checking
def test_check_schema():
    df = create_sample_dataframe()
    report = check_schema(df, null_threshold=0.5)
    assert report.has_issues() == True
    assert 'dob' in report.high_null_cols

# Test for full report
def test_run_full_report():
    df = create_sample_dataframe()
    report = run_full_report(df, source='test_data', key_col='patient_id', critical_cols=['dob', 'diagnosis_code'])
    assert report.row_count == 6
    assert report.col_count == 4
    assert report.nulls.has_issues() == True
    assert report.duplicates.has_issues() == True
    assert report.outliers.has_issues() == True
    assert report.schema.has_issues() == True
    assert report.overall_score < 100  # Expecting some issues to lower the score