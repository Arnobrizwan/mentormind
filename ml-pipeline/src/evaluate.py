"""Stage 3 — evaluate on the held-out test split. Emits metrics.json for
DVC to diff between pipeline runs."""

import json

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from common import DATA_DIR, FEATURES, MODELS_DIR, PIPELINE_DIR, TARGET, load_params


def main():
    threshold = load_params()["evaluate"]["decision_threshold"]
    test = pd.read_csv(DATA_DIR / "test.csv")
    pipeline = joblib.load(MODELS_DIR / "dropout_risk.joblib")

    probs = pipeline.predict_proba(test[FEATURES])[:, 1]
    preds = (probs >= threshold).astype(int)

    metrics = {
        "accuracy": round(float(accuracy_score(test[TARGET], preds)), 4),
        "f1": round(float(f1_score(test[TARGET], preds)), 4),
        "roc_auc": round(float(roc_auc_score(test[TARGET], probs)), 4),
        "test_rows": len(test),
        "positive_rate": round(float(test[TARGET].mean()), 4),
    }
    with open(PIPELINE_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"evaluate: {metrics}")


if __name__ == "__main__":
    main()
