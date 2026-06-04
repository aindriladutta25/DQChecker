import pandas as pd
from dq_checker import run_full_report

# Load sample data
df = pd.read_csv("../tests/sample_data.csv")

# Run the data quality report
report = run_full_report(df, source="Sample Data", key_col="id", critical_cols=["name", "age"])

# Print the summary of the report
print(report.summary())

# Optionally, save the report to a JSON file
with open("data_quality_report.json", "w") as f:
    f.write(report.to_json())