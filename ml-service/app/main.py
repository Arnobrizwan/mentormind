"""MentorMind ML service — FastAPI inference microservice.

Phase 4: OpenCV vision endpoints (proctoring, OMR grading, OCR).
Phase 5: dropout-risk model trained by the DVC/MLflow pipeline.
"""

import json
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from . import dropout, vision
from .flags import flag_enabled

app = FastAPI(title="MentorMind ML Service", version="0.4.0")

INSTANCE_NAME = os.getenv("INSTANCE_NAME", "ml-local")

MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))


def require_flag(key: str) -> None:
    """Live kill switch: flips off from the admin console, no redeploy."""
    if not flag_enabled(key):
        raise HTTPException(
            status_code=403, detail=f"The '{key}' feature is currently disabled."
        )


@app.get("/healthz")
def healthz():
    return {"status": "ok", "instance": INSTANCE_NAME}


@app.get("/v1/models")
def models():
    return {
        "proctoring": {"status": "loaded", "engine": "opencv-haar"},
        "omr_grader": {"status": "loaded", "engine": "opencv-grid"},
        "handwriting_ocr": {
            "status": "loaded" if vision.ocr_available() else "unavailable",
            "engine": "tesseract",
        },
        "dropout_risk": {
            "status": "loaded" if dropout.get_model() else "not_loaded",
            "engine": "logistic-regression (ml-pipeline export)",
        },
    }


class EngagementFeatures(BaseModel):
    progress_pct: float
    days_since_last_login: float
    quiz_avg: float
    lessons_per_week: float
    chat_messages: float


@app.post("/v1/predict/dropout-risk")
def predict_dropout(features: EngagementFeatures):
    """Score a student's dropout risk from engagement features."""
    require_flag("dropout_risk")
    model = dropout.get_model()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="dropout_risk model not loaded — run the ml-pipeline first.",
        )
    probability = model.predict_proba(features.model_dump())
    return {
        "probability": round(probability, 4),
        "risk": dropout.DropoutModel.bucket(probability),
    }


async def _read_image(file: UploadFile):
    raw = await file.read()
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (8 MB max).")
    image = vision.decode_image(raw)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")
    return image


@app.post("/v1/proctor/check")
async def proctor_check(image: UploadFile = File(...)):
    """Webcam-frame proctoring: exactly one face is 'ok'."""
    require_flag("proctoring")
    frame = await _read_image(image)
    return vision.proctor_check(frame)


@app.post("/v1/omr/grade")
async def omr_grade(
    image: UploadFile = File(...),
    answer_key: str = Form(..., description="JSON array of 0-based answers, e.g. [1,0,3]"),
    num_options: int = Form(4),
):
    """Grade a grid-layout bubble sheet against an answer key."""
    require_flag("omr_grading")
    try:
        key = json.loads(answer_key)
        assert isinstance(key, list) and all(isinstance(i, int) for i in key)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(
            status_code=400, detail="answer_key must be a JSON array of integers."
        )
    if not key:
        raise HTTPException(status_code=400, detail="answer_key must not be empty.")
    if not 2 <= num_options <= 10:
        raise HTTPException(status_code=400, detail="num_options must be 2-10.")

    sheet = await _read_image(image)
    return vision.omr_grade(sheet, key, num_options)


@app.post("/v1/ocr/extract")
async def ocr_extract(image: UploadFile = File(...)):
    """Extract printed/handwritten text from a page photo."""
    require_flag("ocr")
    if not vision.ocr_available():
        raise HTTPException(
            status_code=503,
            detail="OCR engine (tesseract) is not installed on this instance.",
        )
    page = await _read_image(image)
    return vision.ocr_extract(page)
