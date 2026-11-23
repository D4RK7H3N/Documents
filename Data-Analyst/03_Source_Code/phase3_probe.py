"""Compute the Phase 3 headline numbers before writing narrative findings."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "02_Datasets" / "cleaned_dataset.csv")

numeric = [
    "age",
    "study_hours_per_week",
    "attendance_percentage",
    "previous_gpa",
    "midterm_score",
    "final_score",
    "academic_risk_index",
]
print("CORRELATIONS WITH final_score")
print(df[numeric].corr()["final_score"].round(3).to_string())
print()
print("MEAN final_score BY grade_band")
print(df.groupby("grade_band", observed=True)["final_score"].agg(["count", "mean"]).round(2).to_string())
print()
print("MEAN final_score BY parental_education")
print(df.groupby("parental_education")["final_score"].agg(["count", "mean"]).round(2).to_string())
print()
print("MEAN final_score BY extracurricular_activities")
print(df.groupby("extracurricular_activities")["final_score"].agg(["count", "mean"]).round(2).to_string())
print()
print("MEAN final_score BY attendance_status")
print(df.groupby("attendance_status", observed=True)["final_score"].agg(["count", "mean"]).round(2).to_string())
print()
print("MEAN final_score BY semester")
print(df.groupby("semester")["final_score"].agg(["count", "mean"]).round(2).to_string())
print()
print("GRADE BAND COUNTS")
print(df["grade_band"].value_counts().to_string())
