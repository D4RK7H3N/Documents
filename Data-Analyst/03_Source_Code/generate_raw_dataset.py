"""Generate the synthetic raw dataset used by this capstone project.

The data is SYNTHETIC. It is generated once with a fixed seed so that the raw
file is immutable for the rest of the pipeline and can be regenerated exactly.
Deliberate quality defects (missing values, invalid ranges, duplicate rows,
inconsistent category labels) are injected so that the cleaning phase has real
work to do and every cleaning decision can be justified from observed evidence.
"""

from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_STATE = 42
N_ROWS = 500
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "02_Datasets" / "raw_dataset.csv"

rng = np.random.default_rng(RANDOM_STATE)

student_id = [f"STU{i:04d}" for i in range(1, N_ROWS + 1)]
age = rng.integers(15, 23, size=N_ROWS)
gender = rng.choice(["Male", "Female", "Other"], size=N_ROWS, p=[0.48, 0.48, 0.04])
study_hours = np.round(np.clip(rng.normal(12, 5, N_ROWS), 0, 35), 1)
attendance = np.round(np.clip(rng.normal(82, 10, N_ROWS), 40, 100), 1)
parental_education = rng.choice(
    ["High School", "Bachelor", "Master", "PhD"],
    size=N_ROWS,
    p=[0.35, 0.40, 0.18, 0.07],
)
extracurricular = rng.choice(["Yes", "No"], size=N_ROWS, p=[0.45, 0.55])
internet_access = rng.choice(["Yes", "No"], size=N_ROWS, p=[0.90, 0.10])
previous_gpa = np.round(np.clip(rng.normal(2.9, 0.6, N_ROWS), 0, 4), 2)

education_level = {"High School": 0, "Bachelor": 1, "Master": 2, "PhD": 3}
edu_num = np.array([education_level[value] for value in parental_education])

final_score = (
    5
    + 1.3 * study_hours
    + 0.25 * attendance
    + 4 * previous_gpa
    + 2.5 * edu_num
    + 3 * (extracurricular == "Yes")
    + 2 * (internet_access == "Yes")
    + rng.normal(0, 4, N_ROWS)
)
final_score = np.round(np.clip(final_score, 0, 100), 1)
midterm_score = np.round(
    np.clip(final_score - rng.normal(2, 3, N_ROWS), 0, 100), 1
)

df = pd.DataFrame(
    {
        "student_id": student_id,
        "age": age,
        "gender": gender,
        "study_hours_per_week": study_hours,
        "attendance_percentage": attendance,
        "parental_education": parental_education,
        "extracurricular_activities": extracurricular,
        "internet_access": internet_access,
        "previous_gpa": previous_gpa,
        "midterm_score": midterm_score,
        "final_score": final_score,
        "semester": rng.choice(
            ["2023-1", "2023-2", "2024-1", "2024-2"], size=N_ROWS
        ),
    }
)

used = set()


def pick(k):
    pool = np.array([i for i in range(N_ROWS) if i not in used])
    chosen = rng.choice(pool, size=k, replace=False)
    used.update(int(i) for i in chosen)
    return chosen


for column, count in [
    ("attendance_percentage", 25),
    ("previous_gpa", 20),
    ("study_hours_per_week", 15),
]:
    df.loc[pick(count), column] = np.nan

df.loc[pick(3), "study_hours_per_week"] = [-2.0, -5.0, -1.0]
df.loc[pick(3), "attendance_percentage"] = [104.0, 110.0, 101.0]
df.loc[pick(4), "study_hours_per_week"] = [85.0, 90.0, 78.0, 95.0]

for column, values in [
    ("gender", ["male", "F", "female", "M", "Other "]),
    ("parental_education", ["bachelors", "Bachelor's", "highschool", "phd", "Master "]),
    ("extracurricular_activities", ["yes", "no", "Y", "N", "Yes "]),
]:
    df.loc[pick(len(values)), column] = values

duplicate_rows = df.iloc[rng.choice(N_ROWS, size=8, replace=False)].copy()
df = pd.concat([df, duplicate_rows], ignore_index=True)
df = df.iloc[rng.permutation(len(df))].reset_index(drop=True)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT, index=False)

print(f"Generated {OUTPUT.relative_to(ROOT)}")
print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
print(f"Exact duplicate rows: {int(df.duplicated().sum())}")
print("Missing values per column:")
print(df.isna().sum()[lambda s: s > 0].to_string())
