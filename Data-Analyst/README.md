# Data Analytics Capstone Project

A reproducible, end-to-end data analytics pipeline: raw data -> cleaned data -> analysis and modeling -> visualizations -> evidence-based recommendations.

**Status:** Complete — all six phases executed. See `RUN_INSTRUCTIONS.md` for a condensed quick start.

## Project structure

```
.
├── 01_Proposal/        Project_Proposal.md
├── 02_Datasets/        raw_dataset.csv (supplied by user), cleaned_dataset.csv,
│                       data_dictionary.csv, cleaning_log.csv
├── 03_Source_Code/     data_cleaning.ipynb, exploratory_analysis.ipynb, data_modeling.ipynb
├── 04_Visualizations/  PNG charts, dashboard/app.py
├── 05_Documentation/   Final_Project_Report.md
├── 06_Presentation/    slide_outline.md
├── requirements.txt
└── README.md
```

## Data

**Integrity notice:** `02_Datasets/raw_dataset.csv` is **synthetic**. It was generated locally with `03_Source_Code/generate_raw_dataset.py` (seed 42) at the project owner's explicit request, overriding the original brief rule that data be user-supplied. See `02_Datasets/DATA_PROVENANCE.md`. Findings demonstrate methodology only and are not evidence about real students.

Regenerate it if needed with:

```powershell
python 03_Source_Code/generate_raw_dataset.py
python 03_Source_Code/profile_raw_data.py
```

Raw data is immutable after generation: never edit it. All cleaning writes to `02_Datasets/cleaned_dataset.csv`.

## Setup

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate` instead. The pins are chosen to have prebuilt wheels on Python 3.11–3.14 (including 3.14), so Windows users do not need a C compiler; `--only-binary=:all:` makes pip fail clearly instead of attempting a source build.

## Execution order

Setup scripts (raw data and Phase 1 evidence):

```powershell
python 03_Source_Code/generate_raw_dataset.py
python 03_Source_Code/profile_raw_data.py
```

Notebooks must be run in order, each with **Restart Kernel and Run All Cells**:

1. `03_Source_Code/data_cleaning.ipynb` -> writes `cleaned_dataset.csv` and `cleaning_log.csv`
2. `03_Source_Code/exploratory_analysis.ipynb` -> statistics, charts, initial findings
3. `03_Source_Code/data_modeling.ipynb` -> tests/models, results table, limitations

The cleaning notebook can be regenerated and executed headlessly from the project root:

```powershell
python 03_Source_Code/build_data_cleaning_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace 03_Source_Code/data_cleaning.ipynb
python 03_Source_Code/export_phase2_summary.py
```

The EDA notebook can likewise be regenerated and executed headlessly; it writes nine PNG charts to `04_Visualizations/`:

```powershell
python 03_Source_Code/build_eda_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace 03_Source_Code/exploratory_analysis.ipynb
python 03_Source_Code/export_notebook_outputs.py 03_Source_Code/exploratory_analysis.ipynb 05_Documentation/phase3_eda_output.txt
```

The modeling notebook writes `05_Documentation/model_results.csv` and three more charts:

```powershell
python 03_Source_Code/build_modeling_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace 03_Source_Code/data_modeling.ipynb
python 03_Source_Code/export_notebook_outputs.py 03_Source_Code/data_modeling.ipynb 05_Documentation/phase4_modeling_output.txt
```

Static PNG snapshots of the dashboard's nine chart views are exported with:

```powershell
python 03_Source_Code/export_dashboard_snapshots.py
```

They are written to `04_Visualizations/dashboard/snapshots/`. Kaleido is pinned to 0.2.1 because 1.x requires a working system Chrome installation; 0.2.1 is self-contained.

Launch the dashboard:

```powershell
streamlit run 04_Visualizations/dashboard/app.py
```

Final submission formats (PDF report/proposal, PPTX presentation) are generated with:

```powershell
python 03_Source_Code/export_submission_formats.py
```

This converts **every `.md` file** in the project to a matching `.pdf` in the same folder (proposal, README, data provenance, EDA report, final report, slide outline) and generates `Final_Presentation.pptx`. It also creates copies named `ArgeLonggakit_StudentAcademicPerformanceAnalysis_*` for the required naming convention.

## Reproducibility rules

- `random_state=42` everywhere randomness is used.
- Versions are pinned in `requirements.txt`.
- Every number in the report must come from executed notebook output; nothing is hand-typed or fabricated.
- Raw data is never modified; all transformations are logged in `cleaning_log.csv`.
- Work in phases and stop for review after each one.

## Phases

1. Setup and data understanding (complete)
2. Cleaning and transformation
3. Exploratory data analysis
4. Analysis and modeling
5. Dashboard
6. Documentation and presentation

## Compliance note

The official `PROJECT-INSTRUCTIONS.docx` expects a dataset downloaded from a reliable source (for example Kaggle) with instructor approval. This project uses synthetic data at the owner's explicit instruction. That is disclosed in `02_Datasets/DATA_PROVENANCE.md`, the proposal, the report, the dashboard and defense question 1, but it remains a grading risk for "Data Collection and Dataset Quality". To make the project fully compliant, supply an instructor-approved dataset at `02_Datasets/raw_dataset.csv` and re-run every script and notebook in the order above.
