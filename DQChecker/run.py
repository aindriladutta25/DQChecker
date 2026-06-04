
import pandas as pd
from src.dq_checker import run_full_report

# Load your DataFrame
df = pd.read_csv("sample_data.csv")

# Run the data quality report
report = run_full_report(df, source="sample_data.csv", key_col="id", critical_cols=["column1", "column2"])

# Print the summary
print(report.summary())