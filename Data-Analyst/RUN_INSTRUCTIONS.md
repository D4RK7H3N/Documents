# Quick Start / Run Instructions

Project: **Arge Longgakit - Student Academic Performance Analysis**

## 1. What is already in the package

The zip already contains all generated results: `cleaned_dataset.csv`, cleaning log, data dictionary, 12 static charts, 9 dashboard snapshots, executed evidence files, all three executed notebooks, PDFs, and `Final_Presentation.pptx`. You do **not** need to re-run anything just to inspect the work.

## 2. Environment setup

Requires Python 3.11 or newer (verified on Python 3.14.5).

**Windows PowerShell** (from the extracted project root):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements.txt
```

`--only-binary=:all:` prevents pip from trying to compile packages from source on machines without a C compiler.

## 3. Launch the dashboard

```powershell
streamlit run 04_Visualizations/dashboard/app.py
```

Open the URL printed in the terminal (normally `http://localhost:8501`). Use the sidebar filters to change all KPIs and charts.

## 4. Reproduce every result from scratch

Run these from the project root, in order:

```powershell
python 03_Source_Code/generate_raw_dataset.py
python 03_Source_Code/profile_raw_data.py

python 03_Source_Code/build_data_cleaning_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace 03_Source_Code/data_cleaning.ipynb
python 03_Source_Code/export_phase2_summary.py

python 03_Source_Code/build_eda_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace 03_Source_Code/exploratory_analysis.ipynb
python 03_Source_Code/export_notebook_outputs.py 03_Source_Code/exploratory_analysis.ipynb 05_Documentation/phase3_eda_output.txt

python 03_Source_Code/build_modeling_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace 03_Source_Code/data_modeling.ipynb
python 03_Source_Code/export_notebook_outputs.py 03_Source_Code/data_modeling.ipynb 05_Documentation/phase4_modeling_output.txt

python 03_Source_Code/export_dashboard_snapshots.py
python 03_Source_Code/export_submission_formats.py
```

Alternatively, open the three notebooks in Jupyter from the project root and use **Restart Kernel and Run All Cells** in the same order (`jupyter notebook`).

## 5. Verify

- All three notebooks must show **0 error outputs**.
- `02_Datasets/cleaned_dataset.csv` should have 500 rows and 15 columns.
- `05_Documentation/model_results.csv` should have 50 metric rows.
- `04_Visualizations/` should contain 12 PNG charts; `04_Visualizations/dashboard/snapshots/` should contain 9 PNGs.
- `06_Presentation/Final_Presentation.pptx` should contain 22 slides.

## 6. Important caveats

- The raw dataset is **synthetic**, generated with seed 42. It is documented in `02_Datasets/DATA_PROVENANCE.md` and disclosed in the report and dashboard. The official project instructions expect a downloaded, instructor-approved dataset; this is a known compliance gap.
- Kaleido is pinned to 0.2.1 because 1.x requires a working system Chrome installation.
- Numerical results in the report trace to the executed evidence files in `05_Documentation/`.
