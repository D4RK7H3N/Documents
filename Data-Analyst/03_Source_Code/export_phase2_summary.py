"""Export a plain-text evidence file for the Phase 2 cleaning results."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
cleaned = pd.read_csv(ROOT / "02_Datasets" / "cleaned_dataset.csv")
log = pd.read_csv(ROOT / "02_Datasets" / "cleaning_log.csv")

lines = [
    "PHASE 2 - CLEANING OUTPUT (from executed data_cleaning.ipynb)",
    "",
    f"Cleaned shape: {cleaned.shape[0]} rows x {cleaned.shape[1]} columns",
    f"Missing values: {int(cleaned.isna().sum().sum())}",
    f"Duplicate rows: {int(cleaned.duplicated().sum())}",
    "Columns: " + ", ".join(cleaned.columns),
    "",
    "CLEANING LOG",
    log[["action", "rows_affected", "rows_before", "rows_after"]].to_string(index=False),
    "",
    "NUMERIC SUMMARY",
    cleaned.describe().T.to_string(),
]

target = ROOT / "05_Documentation" / "phase2_cleaning_output.txt"
target.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Saved {target.relative_to(ROOT)}")
