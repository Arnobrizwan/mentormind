"""MentorMind ML service — FastAPI inference microservice.

Phase 1: skeleton with health + model info endpoints.
Phase 4 adds: proctoring (OpenCV face detection), OMR grading, OCR.
Phase 5 adds: model loading from the MLflow registry + canary serving.
"""

import os

from fastapi import FastAPI

app = FastAPI(title="MentorMind ML Service", version="0.1.0")

INSTANCE_NAME = os.getenv("INSTANCE_NAME", "ml-local")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "instance": INSTANCE_NAME}


@app.get("/v1/models")
def models():
    """Will report loaded model versions from the MLflow registry (Phase 5)."""
    return {
        "proctoring": {"status": "not_loaded", "phase": 4},
        "omr_grader": {"status": "not_loaded", "phase": 4},
        "handwriting_ocr": {"status": "not_loaded", "phase": 4},
        "dropout_risk": {"status": "not_loaded", "phase": 5},
    }
