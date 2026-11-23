"""Compute Phase 4 headline statistics before writing the modeling narrative."""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "02_Datasets" / "cleaned_dataset.csv")

categorical = [
    "gender",
    "parental_education",
    "extracurricular_activities",
    "internet_access",
    "semester",
]
encoded = pd.get_dummies(df, columns=categorical, drop_first=True, dtype=float)
base_predictors = [
    "age",
    "study_hours_per_week",
    "attendance_percentage",
    "previous_gpa",
] + [c for c in encoded.columns if any(c.startswith(p + "_") for p in categorical)]

X = encoded[base_predictors]
y = encoded["final_score"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print("=== REGRESSION (no midterm) ===")
for name, model in [
    ("baseline", DummyRegressor(strategy="mean")),
    ("linear", LinearRegression()),
]:
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    cv = cross_validate(
        model, X_train, y_train, cv=5,
        scoring={"r2": "r2", "rmse": "neg_root_mean_squared_error"},
    )
    print(
        name,
        "test R2=%.3f" % r2_score(y_test, pred),
        "RMSE=%.3f" % np.sqrt(np.mean((y_test - pred) ** 2)),
        "MAE=%.3f" % np.mean(np.abs(y_test - pred)),
        "CV_R2=%.3f" % cv["test_r2"].mean(),
        "CV_RMSE=%.3f" % (-cv["test_rmse"].mean()),
    )

X2 = encoded[base_predictors + ["midterm_score"]]
X2_train, X2_test, _, _ = train_test_split(
    X2, y, test_size=0.2, random_state=42
)
model2 = LinearRegression().fit(X2_train, y_train)
pred2 = model2.predict(X2_test)
print("=== REGRESSION (with midterm) ===")
print("test R2=%.3f" % r2_score(y_test, pred2),
      "RMSE=%.3f" % np.sqrt(np.mean((y_test - pred2) ** 2)))

perm = permutation_importance(
    LinearRegression().fit(X_train, y_train), X_test, y_test,
    scoring="r2", n_repeats=10, random_state=42,
)
order = np.argsort(perm.importances_mean)[::-1]
print("=== PERMUTATION IMPORTANCE (no midterm) ===")
for i in order[:6]:
    print("%s %.3f +/- %.3f" % (
        base_predictors[i], perm.importances_mean[i], perm.importances_std[i]
    ))

print("=== TESTS ===")
r_study, p_study = stats.pearsonr(df["study_hours_per_week"], df["final_score"])
r_att, p_att = stats.pearsonr(df["attendance_percentage"], df["final_score"])
print("study r=%.3f p=%.3g" % (r_study, p_study))
print("attendance r=%.3f p=%.3g" % (r_att, p_att))

groups = [g["final_score"].values for _, g in df.groupby("parental_education")]
f, p = stats.f_oneway(*groups)
grand = df["final_score"].mean()
ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
ss_total = ((df["final_score"] - grand) ** 2).sum()
print("parental edu ANOVA F=%.3f p=%.3g eta2=%.4f" % (f, p, ss_between / ss_total))

a = df.loc[df["extracurricular_activities"] == "Yes", "final_score"]
b = df.loc[df["extracurricular_activities"] == "No", "final_score"]
t, p = stats.ttest_ind(a, b, equal_var=False)
pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
print("extracurricular t=%.3f p=%.3g Cohen_d=%.3f" % (t, p, (a.mean() - b.mean()) / pooled))

groups = [g["final_score"].values for _, g in df.groupby("attendance_status", observed=True)]
f, p = stats.f_oneway(*groups)
ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
print("attendance status ANOVA F=%.3f p=%.3g eta2=%.4f" % (f, p, ss_between / ss_total))

print("=== CLASSIFICATION (Fail vs rest, no midterm) ===")
y_class = (df["grade_band"] == "Fail").astype(int).loc[X.index]
Xc_train, Xc_test, yc_train, yc_test = train_test_split(
    X, y_class, test_size=0.2, random_state=42, stratify=y_class
)
for name, model in [
    ("baseline", DummyClassifier(strategy="most_frequent")),
    ("logreg", LogisticRegression(max_iter=1000, random_state=42)),
]:
    model.fit(Xc_train, yc_train)
    pred = model.predict(Xc_test)
    proba = model.predict_proba(Xc_test)[:, 1]
    cv = cross_validate(
        model, Xc_train, yc_train,
        cv=StratifiedKFold(5, shuffle=True, random_state=42),
        scoring={"f1": "f1", "accuracy": "accuracy"},
    )
    print(
        name,
        "acc=%.3f" % accuracy_score(yc_test, pred),
        "prec=%.3f" % precision_score(yc_test, pred, zero_division=0),
        "rec=%.3f" % recall_score(yc_test, pred),
        "f1=%.3f" % f1_score(yc_test, pred),
        "auc=%.3f" % roc_auc_score(yc_test, proba),
        "CV_F1=%.3f" % cv["test_f1"].mean(),
    )
    if name == "logreg":
        print("confusion", confusion_matrix(yc_test, pred).tolist())

print("=== CLUSTERING ===")
features = df[["study_hours_per_week", "attendance_percentage", "previous_gpa"]]
scaled = StandardScaler().fit_transform(features)
for k in range(2, 9):
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(scaled)
    print("k=%d inertia=%.1f silhouette=%.3f" % (
        k, km.inertia_, __import__("sklearn.metrics", fromlist=["silhouette_score"]).silhouette_score(scaled, km.labels_)
    ))
