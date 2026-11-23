# Presentation Outline and Defense Preparation

## Slide-by-slide content

### Slide 1 — Title
**Student Academic Performance Analysis: A Reproducible End-to-End Analytics Pipeline**
- Name: Arge Longgakit
- Course: Data Analytics 1 / Data Analytics 2
- **Prominent note:** dataset is synthetic; this is a methodology demonstration.

### Slide 2 — Background and Problem
- Institutions collect attendance, study and assessment data; decisions need evidence, not intuition.
- Raw file: 508 rows, 12 columns, with 8 duplicates, 60 missing numeric cells, impossible values and inconsistent labels [E1].
- Problem: produce a trustworthy cleaned dataset, then answer five focused questions.

### Slide 3 — Objectives and Research Questions
- Objectives: clean, explore, test, model, visualise, recommend — all reproducibly.
- RQ1: study hours / attendance vs final score.
- RQ2: parental education and extracurricular group differences.
- RQ3: predicting final score versus a mean-only baseline.
- RQ4: predicting failure (classification).
- RQ5: engagement clusters and semester trends.

### Slide 4 — Dataset and Provenance
- Generated locally with seed 42; no external download; generator included.
- Raw 508×12 → cleaned 500×15, identifier dropped.
- **Disclosure:** synthetic data, so no causal or real-world claims.

### Slide 5 — CRISP-DM Pipeline
- Business/Data Understanding → proposal, profile, dictionary.
- Data Preparation → cleaning log.
- Modeling/Evaluation → tests, models, results table.
- Deployment → Streamlit dashboard.
- Communication → report and this presentation.

### Slide 6 — Cleaning Decisions
- 8 duplicates removed; `student_id` dropped for privacy.
- 4+4+4 label variants unified.
- 3 negative study hours and 3 attendance >100 set to missing.
- 6 study-hour outliers above 24.91 h flagged.
- 24 / 28 / 20 cells imputed with medians 12.10 / 81.85 / 2.93.
- 4 derived variables; validation: 0 missing, 0 duplicates [E2].

### Slide 7 — EDA Findings
- Final score mean 57.74, sd 8.62, range 35.9–88.9 [E3].
- Correlations: midterm 0.943, study 0.696, risk −0.711, age 0.005.
- Attendance High 61.98 vs Low 54.43; Master 60.94 vs High School 54.95.
- Grade bands: Pass 361 (72.2%), Fail 100 (20%) [E3].

### Slide 8 — Statistical Tests
- Study r=0.696 (p=1.3e-73); attendance r=0.306 (p=2.5e-12).
- Parental education η²=0.0696; attendance status η²=0.0806 — under 9% of variance.
- Extracurricular d=0.287 (small).
- Message: effect sizes matter more than p-values at n=500 [E4].

### Slide 9 — Predictive Models
- Regression baseline R²=−0.011; linear model R²=0.703, RMSE 4.62, CV R²=0.723.
- Midterm-inclusive R²=0.891 is a **leakage warning**, not a result.
- Permutation importance: study 0.977, attendance 0.175, GPA 0.145.
- Classification: baseline F1=0; logistic F1=0.629, recall 0.550, AUC 0.914; 9 of 20 failing students missed [E4].

### Slide 10 — Clustering and Limitations
- Best silhouette 0.250 at k=4 → weak structure, no strong profiles claimed.
- Limitations: synthetic data, median-imputation bias, small subgroups (PhD 37, Distinction 1), class imbalance, cross-sectional design, no tuning [E4].

### Slide 11 — Dashboard
- `streamlit run 04_Visualizations/dashboard/app.py` — verified launch.
- 4 KPI cards, 6 sidebar filters, 9 interactive Plotly charts, model-results table, recommendations panel.
- 9 static PNG snapshots exported [E5].

### Slide 12 — Conclusions and Recommendations
- Cleaning produced a validated, privacy-safe dataset with a full decision log.
- Study behaviour dominates; demographic effects are small; fail detection is useful but imperfect.
- Recommendations: prioritise study support, monitor attendance, use classifier only for human-reviewed screening, always report effect sizes, exclude leaking features.
- All findings conditional on synthetic data; future work needs a real, instructor-approved dataset.

---

## Ten likely defense questions (with grounded answers)

**Q1. Why is your dataset synthetic, and does that invalidate the project?**
The owner explicitly asked me to generate data because none was supplied; I disclosed this in `DATA_PROVENANCE.md`, the proposal, the report and the dashboard. It invalidates real-world claims, not the pipeline demonstration. Strictly, the official instructions expect a downloaded, instructor-approved dataset — this is the main compliance gap and must be resolved with the instructor.

**Q2. How do you prove the raw data is reproducible and unmodified?**
`03_Source_Code/generate_raw_dataset.py` regenerates the exact file with `numpy.random.default_rng(42)`. The raw file was written once and never edited; all cleaning writes to `cleaned_dataset.csv`. The profile in E1 is the fingerprint of that raw file.

**Q3. Why did you use median imputation instead of dropping rows?**
There were 72 missing numeric cells across three columns. Dropping affected rows would remove roughly 9% of records and could bias the sample. The median is robust to the skew seen in study hours and attendance. Medians were 12.10, 81.85 and 2.93 [E2].

**Q4. Why is the IQR upper bound 24.91 hours?**
It is Q3 + 1.5×IQR computed after invalid negatives were set to missing. Six values above it (up to 95 h/week) were implausible and flagged as missing, then imputed. The rule is stated in the cleaning notebook [E2].

**Q5. You report R² = 0.703 and also 0.891. Which is correct and why the difference?**
Both are computed outputs, but only 0.703 is used for conclusions. The 0.891 model includes `midterm_score`, which correlates 0.943 with the target and is effectively a near-duplicate. Reporting it as predictive success would be leakage [E4].

**Q6. Why is accuracy a misleading metric here?**
Only 100 of 500 students fail (20%). A dummy classifier that always predicts "not fail" scores 0.800 accuracy but F1 = 0.000. We therefore report F1 (0.629), precision (0.733), recall (0.550) and the confusion matrix `[[76,4],[9,11]]` [E4].

**Q7. Your ANOVA results are significant — are the group differences important?**
Statistically yes, practically modest. Parental education eta² = 0.0696 and attendance status eta² = 0.0806, so each explains under 9% of score variance. Extracurricular Cohen's d = 0.287 is small. Significance partly reflects n = 500 [E4].

**Q8. Why do you say clustering failed?**
Silhouette scores across k = 2–8 range only from 0.220 to 0.250, with the best 0.250 at k = 4. Values near 0.25 indicate weak separation, so we report no strong natural engagement profiles rather than inventing labels [E4].

**Q9. How does the dashboard guarantee the filters actually work?**
`apply_filters()` builds a boolean mask over all six sidebar selections and applies it before every KPI and chart; an empty selection triggers an explicit warning instead of a crash. The app was launched headlessly and served successfully on port 8501, and nine chart snapshots were exported from the same figure-building functions [E5].

**Q10. What would you change with a real, instructor-approved dataset?**
Replace the generator output with a genuine source, document collection and licensing, re-run every notebook unchanged, treat missing data with a principled method where justified, pre-register any class-imbalance strategy to improve recall, validate clusters externally, and only then make domain-specific recommendations. The code structure would remain the same.

---

**Evidence codes** refer to the index in `05_Documentation/Final_Project_Report.md`: E1 raw profile, E2 cleaning, E3 EDA, E4 modeling, E5 dashboard.
