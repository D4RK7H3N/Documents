"""Export static PNG snapshots of the dashboard's key chart views.

Sets DASHBOARD_EXPORT so importing app.py does not start the Streamlit UI,
then writes each Plotly figure to 04_Visualizations/dashboard/snapshots/.
"""

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "04_Visualizations" / "dashboard" / "app.py"
SNAPSHOTS = APP.parent / "snapshots"
EVIDENCE = ROOT / "05_Documentation" / "phase5_dashboard_output.txt"

os.environ["DASHBOARD_EXPORT"] = "1"
spec = importlib.util.spec_from_file_location("dashboard_app", APP)
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)

df = dashboard.load_data()
figures = dashboard.build_figures(df)
SNAPSHOTS.mkdir(parents=True, exist_ok=True)

lines = ["PHASE 5 - DASHBOARD SNAPSHOT EXPORT (executed)"]
lines.append(f"Rows loaded: {len(df)}")
lines.append(f"Charts exported: {len(figures)}")
for name, figure in figures.items():
    target = SNAPSHOTS / f"{name}.png"
    figure.write_image(target, width=1200, height=700)
    lines.append(f"{target.relative_to(ROOT)} ({target.stat().st_size} bytes)")

lines.append("")
lines.append("KPI VALUES (full dataset)")
lines.append(f"Mean final score: {df['final_score'].mean():.2f}")
lines.append(f"Fail rate: {(df['grade_band'] == 'Fail').mean():.2%}")
lines.append(f"Mean study hours: {df['study_hours_per_week'].mean():.2f}")
lines.append(f"Study-score correlation: {df['study_hours_per_week'].corr(df['final_score']):.3f}")

if dashboard.RESULTS.exists():
    results = dashboard.pd.read_csv(dashboard.RESULTS)
    lines.append("")
    lines.append("MODEL METRICS SNAPSHOT")
    key = results[
        ((results["analysis"] == "RQ3 regression") & (results["metric"] == "test_R2"))
        | ((results["analysis"] == "RQ4 classification") & (results["metric"] == "F1"))
    ]
    lines.append(key[["analysis", "method", "metric", "value"]].to_string(index=False))

EVIDENCE.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Exported {len(figures)} snapshots to {SNAPSHOTS.relative_to(ROOT)}")
print(f"Evidence: {EVIDENCE.relative_to(ROOT)}")
