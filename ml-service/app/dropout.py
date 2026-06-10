"""Dropout-risk scoring — serves the artifact exported by ml-pipeline.

The training pipeline flattens its sklearn model into plain JSON weights
(scaler stats + logistic coefficients), so serving needs only numpy and
the image stays free of training dependencies.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(Path(__file__).resolve().parent.parent / "models")))
ARTIFACT_PATH = MODEL_DIR / "dropout_risk.json"


class DropoutModel:
    def __init__(self, artifact: dict):
        self.features: list[str] = artifact["features"]
        self.mean = np.array(artifact["scaler_mean"])
        self.scale = np.array(artifact["scaler_scale"])
        self.coef = np.array(artifact["coef"])
        self.intercept = float(artifact["intercept"])

    def predict_proba(self, payload: dict) -> float:
        x = np.array([float(payload[f]) for f in self.features])
        z = ((x - self.mean) / self.scale) @ self.coef + self.intercept
        return float(1.0 / (1.0 + np.exp(-z)))

    @staticmethod
    def bucket(probability: float) -> str:
        if probability >= 0.66:
            return "high"
        if probability >= 0.33:
            return "medium"
        return "low"


_model: DropoutModel | None = None


def get_model() -> DropoutModel | None:
    global _model
    if _model is None and ARTIFACT_PATH.exists():
        with open(ARTIFACT_PATH) as f:
            _model = DropoutModel(json.load(f))
    return _model
