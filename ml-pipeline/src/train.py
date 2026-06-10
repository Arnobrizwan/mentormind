"""Stage 2 — train the dropout-risk model.

Trains scikit-learn logistic regression, then exports a *dependency-free*
artifact (scaler stats + coefficients as JSON) so the serving side
(ml-service) only needs numpy. Logs the run to MLflow when
MLFLOW_TRACKING_URI is configured; trains identically without it.
"""

import json
import os

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from common import DATA_DIR, FEATURES, MODELS_DIR, TARGET, load_params

MODEL_NAME = "dropout_risk"


def export_portable(pipeline: Pipeline, path):
    """Flatten scaler + logistic regression into plain JSON weights."""
    scaler: StandardScaler = pipeline.named_steps["scaler"]
    clf: LogisticRegression = pipeline.named_steps["clf"]
    artifact = {
        "model": MODEL_NAME,
        "features": FEATURES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coef": clf.coef_[0].tolist(),
        "intercept": float(clf.intercept_[0]),
    }
    with open(path, "w") as f:
        json.dump(artifact, f, indent=2)
    return artifact


def main():
    params = load_params()["train"]
    train = pd.read_csv(DATA_DIR / "train.csv")

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=params["C"], max_iter=params["max_iter"])),
        ]
    )
    pipeline.fit(train[FEATURES], train[TARGET])

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(pipeline, MODELS_DIR / f"{MODEL_NAME}.joblib")
    export_portable(pipeline, MODELS_DIR / f"{MODEL_NAME}.json")
    train_acc = pipeline.score(train[FEATURES], train[TARGET])
    print(f"train: fitted on {len(train)} rows, train accuracy {train_acc:.3f}")

    if os.getenv("MLFLOW_TRACKING_URI"):
        try:
            import mlflow
            import mlflow.sklearn

            mlflow.set_experiment("mentormind-dropout-risk")
            with mlflow.start_run():
                mlflow.log_params(params)
                mlflow.log_metric("train_accuracy", train_acc)
                mlflow.sklearn.log_model(
                    pipeline, name=MODEL_NAME, registered_model_name=MODEL_NAME
                )
            print("train: run logged to MLflow registry")
        except Exception as exc:  # registry down must never block training
            print(f"train: MLflow logging skipped ({exc})")


if __name__ == "__main__":
    main()
