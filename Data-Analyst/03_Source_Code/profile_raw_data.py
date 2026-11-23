"""Profile the immutable raw dataset and build the data dictionary.

This script is executed (not hand-written results) so every number in the
Phase 1 report traces to code output. Its full output is saved to
05_Documentation/phase1_data_profile.txt.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02_Datasets" / "raw_dataset.csv"
DICTIONARY = ROOT / "02_Datasets" / "data_dictionary.csv"
PROFILE = ROOT / "05_Documentation" / "phase1_data_profile.txt"

df = pd.read_csv(RAW)
lines = []


def emit(text=""):
    print(text)
    lines.append(str(text))


emit("PHASE 1 - RAW DATA PROFILE")
emit(f"Source: {RAW.relative_to(ROOT)}")
emit("")
emit("1. SHAPE")
emit(f"Rows: {df.shape[0]} | Columns: {df.shape[1]}")
emit("")
emit("2. DTYPES")
emit(df.dtypes.to_string())
emit("")
emit("3. SAMPLE ROWS (first 5)")
emit(df.head().to_string(index=False))
emit("")
emit("4. UNIQUE COUNTS")
emit(df.nunique().to_string())
emit("")
emit("5. MISSING VALUES")
emit(df.isna().sum().to_string())
emit("")
emit("6. DUPLICATES")
emit(f"Exact duplicate rows: {int(df.duplicated().sum())}")
emit("")
emit("7. SUMMARY STATISTICS (numeric)")
emit(df.describe().T.to_string())
emit("")
emit("8. CATEGORICAL VALUE COUNTS (raw labels, incl. inconsistencies)")
for column in [
    "gender",
    "parental_education",
    "extracurricular_activities",
    "internet_access",
    "semester",
]:
    emit(f"[{column}]")
    emit(df[column].value_counts(dropna=False).to_string())
    emit("")

definitions = {
    "student_id": ("string", "Unique student identifier; personal identifier to be masked or dropped", "identifier (privacy-sensitive)"),
    "age": ("integer", "Student age in years", "predictor / control variable"),
    "gender": ("categorical", "Self-reported gender; raw labels are inconsistent", "categorical predictor"),
    "study_hours_per_week": ("float", "Self-reported weekly study hours; raw data contains negative and extreme values", "key numerical predictor"),
    "attendance_percentage": ("float", "Percentage of classes attended; raw data contains missing and >100 values", "key numerical predictor"),
    "parental_education": ("categorical", "Highest education level of parent/guardian; raw labels are inconsistent", "categorical predictor"),
    "extracurricular_activities": ("categorical", "Participation in extracurricular activities (Yes/No); raw labels are inconsistent", "categorical predictor"),
    "internet_access": ("categorical", "Whether the student has home internet access (Yes/No)", "categorical predictor"),
    "previous_gpa": ("float", "Prior semester GPA on a 0-4 scale; raw data contains missing values", "key numerical predictor"),
    "midterm_score": ("float", "Midterm examination score from 0 to 100", "numerical predictor"),
    "final_score": ("float", "Final examination score from 0 to 100", "primary outcome / target variable"),
    "semester": ("categorical", "Academic semester of record", "grouping and trend variable"),
}

rows = []
for variable, (dtype, description, role) in definitions.items():
    example = df[variable].dropna().iloc[0]
    rows.append(
        {
            "variable": variable,
            "type": dtype,
            "description": description,
            "example": example,
            "analytical role": role,
        }
    )
pd.DataFrame(rows).to_csv(DICTIONARY, index=False)
emit(f"Data dictionary written: {DICTIONARY.relative_to(ROOT)} ({len(rows)} variables)")

PROFILE.parent.mkdir(parents=True, exist_ok=True)
PROFILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
emit(f"Full profile saved: {PROFILE.relative_to(ROOT)}")
