"""Management command: python manage.py train_model

Trains the review sentiment classifier:
  1. Loads a CSV dataset (text,label).
  2. Stratified split: 70% train / 15% validation / 15% test.
  3. Baseline: TF-IDF (1-2 grams) + LogisticRegression.
  4. If baseline validation accuracy is weak (< --weak-threshold, default
     0.85), trains a stronger TF-IDF + XGBoost model and keeps whichever
     scores better on validation.
  5. Reports accuracy / macro-F1 / classification report on the test set.
  6. Saves the winning pipeline to backend/ml/artifacts/model.joblib and
     the metrics to backend/ml/artifacts/metrics.json.
"""
import csv
import json
from datetime import datetime
from pathlib import Path

import joblib
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

RANDOM_SEED = 42
MODEL_VERSION = "1.0.0"
DEFAULT_WEAK_THRESHOLD = 0.85


def build_baseline_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    C=1.0,
                    class_weight="balanced",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def build_strong_pipeline() -> Pipeline:
    from xgboost import XGBClassifier

    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "clf",
                XGBClassifier(
                    n_estimators=300,
                    max_depth=6,
                    learning_rate=0.1,
                    tree_method="hist",
                    eval_metric="mlogloss",
                    n_jobs=-1,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


class Command(BaseCommand):
    help = (
        "Train the sentiment model (TF-IDF + LogisticRegression baseline, "
        "XGBoost fallback when the baseline is weak) and save it to "
        "backend/ml/artifacts/."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            type=str,
            default=None,
            help="Path to the reviews CSV file (default: <repo root>/data/reviews.csv).",
        )
        parser.add_argument(
            "--weak-threshold",
            type=float,
            default=DEFAULT_WEAK_THRESHOLD,
            help=(
                "Validation accuracy below which the stronger XGBoost model is "
                f"trained (default: {DEFAULT_WEAK_THRESHOLD})."
            ),
        )

    def handle(self, *args, **options):
        data_path = (
            Path(options["data"])
            if options["data"]
            else settings.BASE_DIR.parent / "data" / "reviews.csv"
        )
        if not data_path.exists():
            raise CommandError(
                f"Dataset not found at {data_path}. "
                "Generate it first: python data/generate_data.py"
            )

        texts, labels = self._load_dataset(data_path)
        self.stdout.write(f"Loaded {len(texts)} samples from {data_path}")

        encoder = LabelEncoder()
        y = encoder.fit_transform(labels)
        class_names = encoder.classes_.tolist()
        self.stdout.write(f"Classes: {class_names}")

        X_train, X_temp, y_train, y_temp = train_test_split(
            texts, y, test_size=0.30, random_state=RANDOM_SEED, stratify=y
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.50, random_state=RANDOM_SEED, stratify=y_temp
        )
        self.stdout.write(
            f"Split -> train: {len(X_train)}, validation: {len(X_val)}, test: {len(X_test)}"
        )

        # ------------------------------------------------------------------
        # 1. Baseline
        # ------------------------------------------------------------------
        self.stdout.write("Training baseline: TF-IDF + LogisticRegression ...")
        baseline = build_baseline_pipeline()
        baseline.fit(X_train, y_train)
        baseline_val_acc = accuracy_score(y_val, baseline.predict(X_val))
        self.stdout.write(f"Baseline validation accuracy: {baseline_val_acc:.4f}")

        chosen_model = baseline
        model_type = "tfidf_logreg"
        strong_val_acc = None

        # ------------------------------------------------------------------
        # 2. Stronger model, only if the baseline is weak
        # ------------------------------------------------------------------
        if baseline_val_acc < options["weak_threshold"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Baseline is weak (validation accuracy {baseline_val_acc:.4f} "
                    f"< {options['weak_threshold']:.2f}). "
                    "Training stronger model: TF-IDF + XGBoost ..."
                )
            )
            try:
                strong = build_strong_pipeline()
            except ImportError:
                raise CommandError(
                    "XGBoost is required for the stronger model but is not installed. "
                    "Run: pip install -r requirements.txt"
                )
            strong.fit(X_train, y_train)
            strong_val_acc = accuracy_score(y_val, strong.predict(X_val))
            self.stdout.write(f"XGBoost validation accuracy: {strong_val_acc:.4f}")
            if strong_val_acc > baseline_val_acc:
                chosen_model = strong
                model_type = "tfidf_xgboost"
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "XGBoost did not improve on the baseline; keeping the baseline."
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Baseline is strong enough (validation accuracy "
                    f"{baseline_val_acc:.4f} >= {options['weak_threshold']:.2f}); "
                    "skipping the stronger model."
                )
            )

        # ------------------------------------------------------------------
        # 3. Final evaluation on the held-out test set
        # ------------------------------------------------------------------
        y_pred = chosen_model.predict(X_test)
        test_acc = accuracy_score(y_test, y_pred)
        test_f1 = f1_score(y_test, y_pred, average="macro")
        report = classification_report(
            y_test, y_pred, target_names=class_names, digits=4, zero_division=0
        )

        self.stdout.write("")
        self.stdout.write("===== Test set results =====")
        self.stdout.write(f"Model:     {model_type}")
        self.stdout.write(f"Accuracy:  {test_acc:.4f}")
        self.stdout.write(f"Macro F1:  {test_f1:.4f}")
        self.stdout.write(report)

        # ------------------------------------------------------------------
        # 4. Persist artifacts
        # ------------------------------------------------------------------
        artifacts_dir = settings.BASE_DIR / "ml" / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        trained_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        version = f"{model_type}-{MODEL_VERSION}"

        bundle = {
            "pipeline": chosen_model,
            "labels": class_names,
            "version": version,
            "trained_at": trained_at,
            "model_type": model_type,
        }
        model_path = artifacts_dir / "model.joblib"
        joblib.dump(bundle, model_path)

        metrics = {
            "version": version,
            "model_type": model_type,
            "trained_at": trained_at,
            "labels": class_names,
            "train_size": len(X_train),
            "validation_size": len(X_val),
            "test_size": len(X_test),
            "baseline_validation_accuracy": round(float(baseline_val_acc), 4),
            "validation_accuracy": round(
                float(strong_val_acc if model_type == "tfidf_xgboost" else baseline_val_acc),
                4,
            ),
            "test_accuracy": round(float(test_acc), 4),
            "test_macro_f1": round(float(test_f1), 4),
            "test_classification_report": report,
        }
        with (artifacts_dir / "metrics.json").open("w", encoding="utf-8") as fh:
            json.dump(metrics, fh, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Model saved to {model_path}"))
        self.stdout.write(self.style.SUCCESS(f"Metrics saved to {artifacts_dir / 'metrics.json'}"))
        self.stdout.write(
            self.style.SUCCESS("Restart the dev server to load the new model into memory.")
        )

    def _load_dataset(self, data_path: Path):
        texts, labels = [], []
        with data_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or not {"text", "label"}.issubset(reader.fieldnames):
                raise CommandError("CSV must contain 'text' and 'label' columns.")
            for row in reader:
                text = (row.get("text") or "").strip()
                label = (row.get("label") or "").strip().lower()
                if text and label:
                    texts.append(text)
                    labels.append(label)

        if len(texts) < 50:
            raise CommandError(
                f"Dataset too small ({len(texts)} usable rows); need at least 50."
            )
        if len(set(labels)) < 2:
            raise CommandError("Dataset must contain at least 2 distinct labels.")
        return texts, labels
