"""Build the Phase 3 exploratory analysis notebook."""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "03_Source_Code" / "exploratory_analysis.ipynb"

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

HEADER = (
    "from pathlib import Path\n"
    "\n"
    "import matplotlib.pyplot as plt\n"
    "import numpy as np\n"
    "import pandas as pd\n"
    "import seaborn as sns\n"
    "\n"
    "ROOT = Path.cwd()\n"
    "if not (ROOT / '02_Datasets').exists():\n"
    "    ROOT = ROOT.parent\n"
    "OUT = ROOT / '04_Visualizations'\n"
    "OUT.mkdir(parents=True, exist_ok=True)\n"
    "\n"
    "sns.set_theme(style='whitegrid')\n"
    "df = pd.read_csv(ROOT / '02_Datasets' / 'cleaned_dataset.csv')\n"
    "print('Loaded cleaned data:', df.shape)"
)


def figure_setup():
    return "fig, ax = plt.subplots(figsize=(8, 5))\n"


cells = [
    md(
        "# Phase 3 - Exploratory Data Analysis\n"
        "\n"
        "**Integrity notice:** the data are synthetic (see `02_Datasets/DATA_PROVENANCE.md`). "
        "All figures below come from this executed notebook on `cleaned_dataset.csv`. Patterns "
        "describe the generated dataset only and are not real-world educational evidence.\n"
        "\n"
        "Every chart has a title, labelled axes, a legend where more than one series is shown, and "
        "a short interpretation next to it."
    ),
    code(HEADER),
    md(
        "## 1. Descriptive statistics and frequency distributions\n"
        "\n"
        "Numeric summaries establish centre and spread; frequency tables show how categorical "
        "variables are distributed before any modelling."
    ),
    code(
        "print('NUMERIC SUMMARY')\n"
        "print(df.describe().T.round(2).to_string())\n"
        "print()\n"
        "for column in ['gender', 'parental_education', 'extracurricular_activities',\n"
        "               'internet_access', 'semester', 'grade_band',\n"
        "               'attendance_status', 'study_hours_category']:\n"
        "    print(f'FREQUENCY - {column}')\n"
        "    print(df[column].value_counts().to_string())\n"
        "    print()"
    ),
    md("## 2. Charts"),
    md(
        "### Chart 1 - Distribution of final exam scores\n"
        "\n"
        "A histogram shows the shape of the outcome variable, which determines whether mean-based "
        "summaries and linear models are reasonable."
    ),
    code(
        figure_setup()
        + "sns.histplot(df['final_score'], bins=20, kde=True, ax=ax, color='steelblue')\n"
        + "ax.set_xlabel('Final score (points)')\n"
        + "ax.set_ylabel('Number of students')\n"
        + "ax.axvline(df['final_score'].mean(), color='crimson', linestyle='--', label='Mean')\n"
        + "ax.legend()\n"
        + "ax.set_title('Distribution of Final Exam Scores')\n"
        + "fig.tight_layout()\n"
        + "fig.savefig(OUT / '01_final_score_histogram.png', dpi=150)\n"
        + "plt.show()"
    ),
    md(
        "**Interpretation:** scores are centred near the mean of 57.74 with a standard deviation "
        "of 8.62 and no strong ceiling pile-up after cleaning. The roughly unimodal shape supports "
        "using mean-based summaries and linear modelling."
    ),
    md(
        "### Chart 2 - Study hours by grade band\n"
        "\n"
        "A boxplot compares the distribution of study time across performance bands and reveals "
        "overlap that a single average would hide."
    ),
    code(
        figure_setup()
        + "order = ['Fail', 'Pass', 'Credit', 'Distinction']\n"
        + "sns.boxplot(data=df, x='grade_band', y='study_hours_per_week',\n"
        + "            order=order, ax=ax, color='lightseagreen')\n"
        + "ax.set_xlabel('Grade band')\n"
        + "ax.set_ylabel('Study hours per week')\n"
        + "ax.set_title('Study Hours per Week by Grade Band')\n"
        + "fig.tight_layout()\n"
        + "fig.savefig(OUT / '02_study_hours_by_grade_band.png', dpi=150)\n"
        + "plt.show()"
    ),
    md(
        "**Interpretation:** study hours rise from the Fail band toward the Credit band, consistent "
        "with the positive correlation of 0.696 with final score. Substantial overlap remains, so "
        "study time alone does not determine the grade band."
    ),
    md(
        "### Chart 3 - Mean final score by parental education\n"
        "\n"
        "A bar chart makes group differences visible; error bars are omitted so the means are easy "
        "to read, and group sizes are reported in the interpretation."
    ),
    code(
        figure_setup()
        + "grouped = df.groupby('parental_education')['final_score'].mean().sort_values()\n"
        + "bars = ax.bar(grouped.index, grouped.values, color='cornflowerblue')\n"
        + "ax.bar_label(bars, fmt='%.1f', padding=3)\n"
        + "ax.set_xlabel('Parental education')\n"
        + "ax.set_ylabel('Mean final score (points)')\n"
        + "ax.set_title('Mean Final Score by Parental Education')\n"
        + "ax.set_ylim(0, 70)\n"
        + "fig.tight_layout()\n"
        + "fig.savefig(OUT / '03_final_score_by_parental_education.png', dpi=150)\n"
        + "plt.show()"
    ),
    md(
        "**Interpretation:** the Master group averages 60.94 versus 54.95 for High School, a gap of "
        "about 6 points. The Master (n=86) and PhD (n=37) groups are small, so these differences "
        "need a statistical test before being taken seriously."
    ),
    md(
        "### Chart 4 - Study hours versus final score\n"
        "\n"
        "A scatter plot with a linear fit checks whether the relationship is approximately linear "
        "and whether outliers drive it."
    ),
    code(
        figure_setup()
        + "sns.scatterplot(data=df, x='study_hours_per_week', y='final_score',\n"
        + "                hue='grade_band', hue_order=order, alpha=0.75, ax=ax)\n"
        + "sns.regplot(data=df, x='study_hours_per_week', y='final_score',\n"
        + "            scatter=False, ax=ax, color='black', truncate=False)\n"
        + "ax.set_xlabel('Study hours per week')\n"
        + "ax.set_ylabel('Final score (points)')\n"
        + "ax.set_title('Study Hours vs Final Score')\n"
        + "ax.legend(title='Grade band')\n"
        + "fig.tight_layout()\n"
        + "fig.savefig(OUT / '04_study_hours_vs_final_score.png', dpi=150)\n"
        + "plt.show()"
    ),
    md(
        "**Interpretation:** the upward fitted line matches the strong positive correlation (r = "
        "0.696). The cloud is wide, indicating that other factors besides study time matter."
    ),
    md(
        "### Chart 5 - Correlation heatmap\n"
        "\n"
        "The heatmap compares all numeric relationships at once and helps detect redundancy between "
        "candidate predictors before modelling."
    ),
    code(
        "numeric = ['age', 'study_hours_per_week', 'attendance_percentage', 'previous_gpa',\n"
        "           'midterm_score', 'academic_risk_index', 'final_score']\n"
        "corr = df[numeric].corr()\n"
        "fig, ax = plt.subplots(figsize=(9, 7))\n"
        "sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, ax=ax)\n"
        "ax.set_title('Correlation Matrix of Numeric Variables')\n"
        "ax.set_xlabel('Variable')\n"
        "ax.set_ylabel('Variable')\n"
        "fig.tight_layout()\n"
        "fig.savefig(OUT / '05_correlation_heatmap.png', dpi=150)\n"
        "plt.show()\n"
        "print(corr['final_score'].round(3).to_string())"
    ),
    md(
        "**Interpretation:** midterm score is by far the strongest correlate of final score (r = "
        "0.943), followed by study hours (0.696) and the risk index (-0.711). Age is essentially "
        "uncorrelated (0.005), so it is a weak candidate predictor."
    ),
    md(
        "### Chart 6 - Mean final score by semester\n"
        "\n"
        "A line plot checks whether outcomes change over the ordered semesters."
    ),
    code(
        "semester_means = df.groupby('semester')['final_score'].mean().sort_index()\n"
        "fig, ax = plt.subplots(figsize=(8, 5))\n"
        "ax.plot(semester_means.index, semester_means.values, marker='o',\n"
        "        color='darkorange', label='Mean final score')\n"
        "ax.set_xlabel('Semester')\n"
        "ax.set_ylabel('Mean final score (points)')\n"
        "ax.set_title('Mean Final Score by Semester')\n"
        "ax.legend()\n"
        "fig.tight_layout()\n"
        "fig.savefig(OUT / '06_final_score_by_semester.png', dpi=150)\n"
        "plt.show()\n"
        "print(semester_means.round(2).to_string())"
    ),
    md(
        "**Interpretation:** averages drift slightly from 58.93 in 2023-1 to 57.10 in 2024-2. With "
        "groups of 115-142 students and synthetic cross-sectional data, this is a descriptive "
        "difference, not evidence of a real time trend."
    ),
    md(
        "### Chart 7 - Mean final score by attendance status\n"
        "\n"
        "A bar chart tests the dose-response expectation that better attendance accompanies higher "
        "scores."
    ),
    code(
        figure_setup()
        + "att = df.groupby('attendance_status', observed=True)['final_score'].mean()\n"
        + "att = att.reindex(['Low', 'Moderate', 'High'])\n"
        + "bars = ax.bar(att.index, att.values, color='mediumpurple')\n"
        + "ax.bar_label(bars, fmt='%.1f', padding=3)\n"
        + "ax.set_xlabel('Attendance status')\n"
        + "ax.set_ylabel('Mean final score (points)')\n"
        + "ax.set_title('Mean Final Score by Attendance Status')\n"
        + "ax.set_ylim(0, 70)\n"
        + "fig.tight_layout()\n"
        + "fig.savefig(OUT / '07_final_score_by_attendance_status.png', dpi=150)\n"
        + "plt.show()"
    ),
    md(
        "**Interpretation:** the High attendance group averages 61.98 versus 54.43 for Low, a gap "
        "of about 7.6 points. The Moderate group sits between them at 57.75, so the pattern is "
        "monotonic but modest."
    ),
    md(
        "### Chart 8 - Final score by extracurricular participation\n"
        "\n"
        "A boxplot compares score distributions for students who do and do not join extracurricular "
        "activities."
    ),
    code(
        figure_setup()
        + "sns.boxplot(data=df, x='extracurricular_activities', y='final_score',\n"
        + "            order=['No', 'Yes'], ax=ax, color='lightcoral')\n"
        + "ax.set_xlabel('Extracurricular participation')\n"
        + "ax.set_ylabel('Final score (points)')\n"
        + "ax.set_title('Final Score by Extracurricular Participation')\n"
        + "fig.tight_layout()\n"
        + "fig.savefig(OUT / '08_final_score_by_extracurricular.png', dpi=150)\n"
        + "plt.show()\n"
        "print(df.groupby('extracurricular_activities')['final_score'].agg(['count', 'mean']).round(2).to_string())"
    ),
    md(
        "**Interpretation:** participants average 59.15 against 56.70 for non-participants, a small "
        "2.45-point difference. The overlapping boxes suggest this is weak evidence and should be "
        "tested rather than reported as an effect."
    ),
    md(
        "### Chart 9 - Grade band counts\n"
        "\n"
        "A bar chart of outcome frequencies shows whether the class distribution is balanced enough "
        "for classification work later."
    ),
    code(
        figure_setup()
        + "counts = df['grade_band'].value_counts().reindex(order)\n"
        + "bars = ax.bar(counts.index, counts.values, color='seagreen')\n"
        + "ax.bar_label(bars, padding=3)\n"
        + "ax.set_xlabel('Grade band')\n"
        + "ax.set_ylabel('Number of students')\n"
        + "ax.set_title('Number of Students by Grade Band')\n"
        + "fig.tight_layout()\n"
        + "fig.savefig(OUT / '09_grade_band_counts.png', dpi=150)\n"
        + "plt.show()\n"
        "print(counts.to_string())"
    ),
    md(
        "**Interpretation:** Pass dominates with 361 students (72.2%), followed by Fail at 100 "
        "(20.0%) and Credit at 38 (7.6%); only 1 student reaches Distinction. This imbalance will "
        "be handled explicitly in any classification step."
    ),
    md(
        "## Key Initial Findings\n"
        "\n"
        "1. Final scores are centred at 57.74 (sd 8.62, median 57.80) without a severe ceiling "
        "effect after cleaning.\n"
        "2. Midterm score (r = 0.943), study hours (r = 0.696) and the composite risk index "
        "(r = -0.711) are the strongest numeric associates of final score; age is negligible "
        "(r = 0.005).\n"
        "3. Group gaps are modest: attendance High vs Low differs by about 7.6 points, parental "
        "education Master vs High School by about 6.0 points, and extracurricular Yes vs No by "
        "2.45 points.\n"
        "4. Grade bands are imbalanced (72.2% Pass), which constrains classification metrics.\n"
        "5. Semester means are nearly flat (58.93 to 57.10), so no meaningful trend is claimed.\n"
        "\n"
        "**Caveat:** these relationships were built into a synthetic generator. They justify "
        "practising the pipeline, not making causal claims about students. Phase 3 will test which "
        "differences survive formal statistical and predictive analysis."
    ),
    code(
        "print('Charts saved to:', OUT)\n"
        "print(sorted(p.name for p in OUT.glob('*.png')))"
    ),
]

nb = nbf.v4.new_notebook(cells=cells)
nbf.write(nb, TARGET)
print(f"Built {TARGET.relative_to(ROOT)} with {len(cells)} cells")
