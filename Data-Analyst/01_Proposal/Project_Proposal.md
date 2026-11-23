# Project Proposal

**Prepared by:** Arge Longgakit

## Title

Student Academic Performance Analysis: A Reproducible End-to-End Analytics Pipeline

## Background

Understanding which factors accompany academic performance is a recurring problem in education analytics. Weekly study time, class attendance, prior grades, and home support are routinely collected, but their relative association with exam outcomes is often asserted rather than measured. This project demonstrates how to move from a raw student record to documented, reproducible evidence.

**Integrity notice:** the dataset is synthetic (see `02_Datasets/DATA_PROVENANCE.md`). It was generated at the project owner's request to enable the full pipeline when no real dataset was available. Findings therefore illustrate methodology and must not be presented as real-world evidence about students.

## Problem Statement

The available record contains 508 rows and 12 variables describing student demographics, study habits, and assessment scores. However, the raw file includes missing values, exact duplicate rows, invalid numeric ranges, and inconsistent category labels. The problem this project addresses is twofold: (1) produce a trustworthy cleaned dataset through documented decisions, and (2) use that dataset to answer specific questions about the association between study behaviors and final exam performance, with honest statements of uncertainty.

Evidence base: the executed profile in `05_Documentation/phase1_data_profile.txt` reports 15 missing study-hour values, 25 missing attendance values, 20 missing prior-GPA values, 8 exact duplicate rows, negative study hours (minimum -5.0), attendance above 100 (maximum 110.0), and inconsistent category labels (8 raw gender labels, 9 raw parental-education labels, 7 raw extracurricular labels).

## Research Questions

1. **How are weekly study hours and attendance percentage associated with final exam scores?** Justified by `study_hours_per_week`, `attendance_percentage`, and `final_score`; addressed with correlation and regression.
2. **Do final scores differ by parental education and extracurricular participation?** Justified by `parental_education`, `extracurricular_activities`, and `final_score`; addressed with group comparisons and effect sizes.
3. **How well can final scores be predicted from study habits, prior GPA, and midterm score compared with a mean-only baseline?** Justified by `previous_gpa`, `midterm_score` and the study/attendance variables against `final_score`; addressed with a train/test split, cross-validation, and R²/RMSE/MAE.
4. **Can students be grouped into distinct engagement profiles?** Justified by study hours, attendance, and prior GPA; addressed optionally with clustering and elbow/silhouette evidence.
5. **How do average final scores vary across semesters?** Justified by `semester` and `final_score`; addressed with grouped trends. Any observed difference is descriptive only, because the data are synthetic and not a true longitudinal design.

## Objectives

1. Define the problem and answerable research questions.
2. Document, clean, and transform the data with every decision logged.
3. Perform exploratory data analysis with descriptive statistics, distributions, correlations, and group comparisons.
4. Apply analytical methods appropriate to the questions and data, with a baseline for comparison.
5. Build visualizations and an interactive Streamlit dashboard.
6. Write a five-chapter report in which every figure traces to executed code output.
7. Prepare a presentation outline and defense material.

## Dataset Source

- Dataset name: Synthetic Student Academic Performance Dataset (v1)
- Source / URL: none — generated locally; not downloaded from any external source
- Generator: `03_Source_Code/generate_raw_dataset.py` with `numpy.random.default_rng(42)`
- Raw file: `02_Datasets/raw_dataset.csv` (508 rows x 12 columns; treated as immutable after generation)
- Variables and collection method: fully documented in `02_Datasets/data_dictionary.csv`, `02_Datasets/DATA_PROVENANCE.md`, and `05_Documentation/phase1_data_profile.txt`

## Methodology Overview

CRISP-DM: Business Understanding -> Data Understanding -> Data Preparation -> Modeling -> Evaluation -> Deployment. Each project phase is mapped to these stages in Chapter 3 of the final report.

## Expected Deliverables

Cleaned dataset, data dictionary, cleaning log, three executed notebooks, at least eight EDA charts, a Streamlit dashboard, the five-chapter final report, and a presentation outline with defense questions.
