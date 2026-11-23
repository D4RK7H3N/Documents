# Exploratory Data Analysis Report

**Prepared by:** Arge Longgakit

**Evidence source:** `05_Documentation/phase3_eda_output.txt` (executed `03_Source_Code/exploratory_analysis.ipynb`), code E3 in the Final Project Report.

**Integrity notice:** data are synthetic; findings describe the generated dataset only.

## 1. Dataset Used

Cleaned dataset: 500 rows × 15 columns, 0 missing values, 0 duplicates. Outcome: `final_score`.

## 2. Descriptive Statistics

`final_score`: mean 57.74, standard deviation 8.62, median 57.80, minimum 35.90, maximum 88.90. `study_hours_per_week`: mean 11.92 (sd 4.76). `attendance_percentage`: mean 81.40 (sd 9.83). `previous_gpa`: mean 2.91 (sd 0.56). `midterm_score`: mean 55.74 (sd 9.22).

## 3. Frequency Distributions

Grade bands: Pass 361, Fail 100, Credit 38, Distinction 1. Gender: Female 245 and other categories after label standardisation. Parental education: Bachelor 192, High School 185, Master 86, PhD 37. Semesters: 2023-1 122, 2023-2 121, 2024-1 142, 2024-2 115.

## 4. Correlation Analysis

Pearson correlations with `final_score`: midterm 0.943, study hours 0.696, academic risk index −0.711, attendance 0.306, prior GPA 0.245, age 0.005. The midterm value is a leakage warning, not a finding to exploit. Age shows no useful linear association.

## 5. Group Comparisons

| Grouping | Means (points) |
|---|---|
| Attendance status | Low 54.43, Moderate 57.75, High 61.98 |
| Parental education | High School 54.95, PhD 58.62, Bachelor 58.82, Master 60.94 |
| Extracurricular | No 56.70, Yes 59.15 |
| Semester | 2023-1 58.93, 2023-2 57.90, 2024-1 57.09, 2024-2 57.10 |

## 6. Charts Produced

Nine charts in `04_Visualizations/`: final-score histogram, study hours by grade band (boxplot), parental-education means (bar), study hours vs final score (scatter with fit), correlation heatmap, semester means (line), attendance-status means (bar), extracurricular boxplot, grade-band counts (bar). Each has a title, labelled axes, a legend where applicable and a written interpretation in the notebook.

## 7. Key Initial Findings

1. Final scores are centred at 57.74 (sd 8.62, median 57.80) without a severe ceiling effect.
2. Study hours (0.696) and the composite risk index (−0.711) are the strongest non-leaking numeric associates.
3. Group gaps are modest: about 7.6 points for attendance, 6.0 for parental education, 2.45 for extracurricular participation.
4. Grade bands are imbalanced (72.2% Pass), which constrains classification metrics.
5. Semester means are nearly flat (58.93 → 57.10); no trend is claimed.

**Caveat:** these relationships were built into a synthetic generator. They justify practising the pipeline, not causal claims about students.
