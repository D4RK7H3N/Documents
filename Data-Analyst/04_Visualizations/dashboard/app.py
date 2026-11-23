"""Streamlit dashboard for the synthetic student performance dataset.

Run from the project root with:
    streamlit run 04_Visualizations/dashboard/app.py

The figure-building functions are separated from the UI so snapshots can be
exported without starting a Streamlit server.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "02_Datasets" / "cleaned_dataset.csv"
RESULTS = ROOT / "05_Documentation" / "model_results.csv"
SNAPSHOTS = ROOT / "04_Visualizations" / "dashboard" / "snapshots"

GRADE_ORDER = ["Fail", "Pass", "Credit", "Distinction"]
NUMERIC = [
    "age",
    "study_hours_per_week",
    "attendance_percentage",
    "previous_gpa",
    "midterm_score",
    "academic_risk_index",
    "final_score",
]


def load_data():
    return pd.read_csv(DATA)


def build_figures(df):
    figures = {}

    fig = px.histogram(
        df, x="final_score", nbins=20,
        title="Distribution of Final Exam Scores",
    )
    fig.update_layout(
        xaxis_title="Final score (points)",
        yaxis_title="Number of students",
        bargap=0.05,
    )
    figures["01_score_distribution"] = fig

    fig = px.box(
        df, x="grade_band", y="study_hours_per_week",
        category_orders={"grade_band": GRADE_ORDER},
        title="Study Hours by Grade Band",
    )
    fig.update_layout(
        xaxis_title="Grade band",
        yaxis_title="Study hours per week",
    )
    figures["02_study_hours_by_grade_band"] = fig

    fig = px.scatter(
        df, x="study_hours_per_week", y="final_score",
        color="grade_band", category_orders={"grade_band": GRADE_ORDER},
        title="Study Hours vs Final Score",
    )
    coefficients = np.polyfit(df["study_hours_per_week"], df["final_score"], 1)
    line_x = np.linspace(
        df["study_hours_per_week"].min(), df["study_hours_per_week"].max(), 100
    )
    fig.add_trace(
        go.Scatter(
            x=line_x, y=np.polyval(coefficients, line_x),
            mode="lines", name="Linear fit", line=dict(color="black", dash="dash"),
        )
    )
    fig.update_layout(
        xaxis_title="Study hours per week",
        yaxis_title="Final score (points)",
        legend_title="Grade band",
    )
    figures["03_study_vs_score"] = fig

    means = df.groupby("parental_education")["final_score"].mean().sort_values()
    fig = px.bar(
        x=means.index, y=means.values,
        title="Mean Final Score by Parental Education",
        labels={"x": "Parental education", "y": "Mean final score (points)"},
        text=np.round(means.values, 1),
    )
    fig.update_layout(yaxis_range=[0, 75])
    figures["04_education_means"] = fig

    correlation = df[NUMERIC].corr()
    fig = px.imshow(
        correlation, text_auto=".2f", zmin=-1, zmax=1,
        color_continuous_scale="RdBu_r",
        title="Correlation Matrix of Numeric Variables",
    )
    fig.update_layout(
        xaxis_title="Variable", yaxis_title="Variable",
    )
    figures["05_correlation_heatmap"] = fig

    semester_means = df.groupby("semester")["final_score"].mean().sort_index()
    fig = px.line(
        x=semester_means.index, y=semester_means.values, markers=True,
        title="Mean Final Score by Semester",
        labels={"x": "Semester", "y": "Mean final score (points)"},
    )
    figures["06_semester_trend"] = fig

    attendance_means = (
        df.groupby("attendance_status", observed=True)["final_score"]
        .mean().reindex(["Low", "Moderate", "High"])
    )
    fig = px.bar(
        x=attendance_means.index, y=attendance_means.values,
        title="Mean Final Score by Attendance Status",
        labels={"x": "Attendance status", "y": "Mean final score (points)"},
        text=np.round(attendance_means.values, 1),
    )
    fig.update_layout(yaxis_range=[0, 75])
    figures["07_attendance_means"] = fig

    band_counts = df["grade_band"].value_counts().reindex(GRADE_ORDER).fillna(0)
    fig = px.bar(
        x=band_counts.index, y=band_counts.values,
        title="Students by Grade Band",
        labels={"x": "Grade band", "y": "Number of students"},
        text=band_counts.values,
    )
    figures["08_grade_band_counts"] = fig

    if RESULTS.exists():
        results = pd.read_csv(RESULTS)
        metric_rows = results[
            (results["analysis"] == "RQ3 regression")
            & (results["metric"] == "test_R2")
        ]
        metric_rows = pd.concat(
            [
                metric_rows,
                results[
                    (results["analysis"] == "RQ4 classification")
                    & (results["metric"] == "F1")
                ],
            ]
        )
        fig = px.bar(
            metric_rows, x="method", y="value", color="analysis",
            barmode="group", title="Baseline vs Model Performance",
            labels={"method": "Method", "value": "Metric value",
                    "analysis": "Analysis"},
            text=np.round(metric_rows["value"].values, 3),
        )
        figures["09_model_comparison"] = fig

    return figures


def apply_filters(df):
    st.sidebar.header("Filters")

    def multiselect(label, column):
        options = sorted(df[column].dropna().unique().tolist())
        selected = st.sidebar.multiselect(label, options, default=options)
        return selected

    genders = multiselect("Gender", "gender")
    education = multiselect("Parental education", "parental_education")
    extracurricular = multiselect("Extracurricular participation", "extracurricular_activities")
    semesters = multiselect("Semester", "semester")

    hours_min, hours_max = float(df["study_hours_per_week"].min()), float(df["study_hours_per_week"].max())
    study_range = st.sidebar.slider(
        "Study hours per week", hours_min, hours_max, (hours_min, hours_max)
    )
    att_min, att_max = float(df["attendance_percentage"].min()), float(df["attendance_percentage"].max())
    attendance_range = st.sidebar.slider(
        "Attendance percentage", att_min, att_max, (att_min, att_max)
    )

    mask = (
        df["gender"].isin(genders)
        & df["parental_education"].isin(education)
        & df["extracurricular_activities"].isin(extracurricular)
        & df["semester"].isin(semesters)
        & df["study_hours_per_week"].between(*study_range)
        & df["attendance_percentage"].between(*attendance_range)
    )
    return df[mask]


def main():
    st.set_page_config(page_title="Student Performance Dashboard", layout="wide")
    st.title("Student Academic Performance Dashboard")
    st.caption(
        "Prepared by Arge Longgakit | Synthetic data for methodology demonstration only - "
        "no claims about real students. See 02_Datasets/DATA_PROVENANCE.md."
    )

    df = load_data()
    filtered = apply_filters(df)

    if filtered.empty:
        st.warning("No students match the current filters. Adjust the sidebar selections.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Students", len(filtered))
    col2.metric("Mean final score", f"{filtered['final_score'].mean():.1f}")
    col3.metric("Fail rate", f"{(filtered['grade_band'] == 'Fail').mean():.1%}")
    col4.metric("Mean study hours", f"{filtered['study_hours_per_week'].mean():.1f}")

    figures = build_figures(filtered)
    for name, figure in figures.items():
        st.plotly_chart(figure, width="stretch", key=name)

    st.subheader("Model Results")
    if RESULTS.exists():
        results = pd.read_csv(RESULTS)
        summary = results[
            results["analysis"].isin(["RQ3 regression", "RQ4 classification"])
        ].pivot_table(
            index=["analysis", "method"], columns="metric", values="value", aggfunc="first"
        ).reset_index()
        st.dataframe(summary, use_container_width=True)
        st.caption(
            "Midterm-inclusive regression (R2 0.891) is reported only as a leakage warning. "
            "Full metric history: 05_Documentation/model_results.csv"
        )
    else:
        st.info("Run the modeling notebook to generate model_results.csv.")

    st.subheader("Recommendations Panel")
    r_study = filtered["study_hours_per_week"].corr(filtered["final_score"])
    st.markdown(
        f"- **Study habits are the strongest modifiable associate** in these data "
        f"(correlation {r_study:.2f} in the current selection; permutation importance 0.977 "
        "in the modeling notebook). Prioritise study support over demographic targeting.\n"
        "- **Attendance matters:** High attendance averages 61.98 versus 54.43 for Low attendance, "
        "a 7.6-point gap.\n"
        "- **Use the fail classifier as a screening aid, not a decision:** F1 0.629 but recall 0.550 "
        "means many at-risk students would be missed.\n"
        "- **Interpret group gaps cautiously:** the Master vs High School gap is about 6 points, "
        "with small subgroups behind it.\n"
        "- **Caveat:** all figures come from synthetic data and describe the generator, not real "
        "students. No causal claim is made."
    )


if os.environ.get("DASHBOARD_EXPORT") != "1":
    main()
