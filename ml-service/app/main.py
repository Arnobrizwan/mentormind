"""MentorMind ML service — FastAPI inference microservice.

Phase 4: OpenCV vision endpoints (proctoring, OMR grading, OCR).
Phase 5: dropout-risk model trained by the DVC/MLflow pipeline.
Plus: the Cambridge past-paper OCR + alignment training pipeline.
"""

import json
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from . import env as _env  # loads .env BEFORE siblings read their knobs
from . import dropout, flashcards, grading, quizgen, vision
from .auth import require_api_key
from .flags import flag_enabled
from .pastpapers import answering
from .pastpapers import api as pastpapers_api
from .pastpapers import browse
from .pastpapers.models import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from .pastpapers.bootstrap import bootstrap_corpus
    bootstrap_corpus()
    await init_db()
    yield


app = FastAPI(title="MentorMind ML Service", version="0.5.0", lifespan=lifespan)
# Pipeline routes get the global key on top of their own PIPELINE_API_TOKEN.
app.include_router(pastpapers_api.router, dependencies=[Depends(require_api_key)])
# Read-only past-paper browsing for the frontend paper browser.
app.include_router(browse.router, dependencies=[Depends(require_api_key)])

# /metrics for the Prometheus scrape job — deliberately outside the API key.
Instrumentator().instrument(app).expose(app)

INSTANCE_NAME = os.getenv("INSTANCE_NAME", "ml-local")

MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))


async def require_flag(key: str) -> None:
    """Live kill switch: flips off from the admin console, no redeploy."""
    if not await flag_enabled(key):
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


@app.post("/v1/predict/dropout-risk", dependencies=[Depends(require_api_key)])
async def predict_dropout(features: EngagementFeatures):
    """Score a student's dropout risk from engagement features."""
    await require_flag("dropout_risk")
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


@app.post("/v1/proctor/check", dependencies=[Depends(require_api_key)])
async def proctor_check(image: UploadFile = File(...)):
    """Webcam-frame proctoring: exactly one face is 'ok'."""
    await require_flag("proctoring")
    frame = await _read_image(image)
    return vision.proctor_check(frame)


@app.post("/v1/omr/grade", dependencies=[Depends(require_api_key)])
async def omr_grade(
    image: UploadFile = File(...),
    answer_key: str = Form(..., description="JSON array of 0-based answers, e.g. [1,0,3]"),
    num_options: int = Form(4),
):
    """Grade a grid-layout bubble sheet against an answer key."""
    await require_flag("omr_grading")
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
    if any(not 0 <= v < num_options for v in key):
        raise HTTPException(
            status_code=400,
            detail=f"answer_key values must be within [0, {num_options}).",
        )

    sheet = await _read_image(image)
    return vision.omr_grade(sheet, key, num_options)


@app.post("/v1/ocr/extract", dependencies=[Depends(require_api_key)])
async def ocr_extract(image: UploadFile = File(...)):
    """Extract printed/handwritten text from a page photo."""
    await require_flag("ocr")
    if not vision.ocr_available():
        raise HTTPException(
            status_code=503,
            detail="OCR engine (tesseract) is not installed on this instance.",
        )
    page = await _read_image(image)
    return vision.ocr_extract(page)


class ShortAnswerGradeRequest(BaseModel):
    # bounded so one giant submission can't hog the grader
    question: str = Field(..., max_length=4000)
    student_answer: str = Field(..., min_length=1, max_length=8000)
    mark_scheme: str = Field(..., min_length=1, max_length=8000)
    max_score: int = Field(5, ge=1, le=100)


@app.post("/v1/grade/short-answer", dependencies=[Depends(require_api_key)])
async def grade_short_answer(request: ShortAnswerGradeRequest):
    """Rubric-based grading of a free-text answer against a mark scheme.
    Returns {score, max_score, criteria_met, criteria_missing, feedback,
    engine} — engine is 'llm' or 'heuristic' (criterion-overlap fallback)."""
    await require_flag("short_answer_grading")
    if not request.student_answer.strip():
        raise HTTPException(status_code=400, detail="student_answer is required.")
    return await grading.grade_short_answer(
        request.question,
        request.student_answer,
        request.mark_scheme,
        request.max_score,
    )


class FlashcardGenerateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=16000)
    topic: str = Field("", max_length=200)
    count: int = Field(10, ge=1, le=20)


@app.post("/v1/generate/flashcards", dependencies=[Depends(require_api_key)])
async def generate_flashcards(request: FlashcardGenerateRequest):
    """Draft spaced-repetition flashcards from lesson content. Returns
    {cards: [{front, back}], engine: 'llm'|'heuristic'} — the caller is
    expected to hold drafts for human review."""
    await require_flag("flashcard_generation")
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content is required.")
    return await flashcards.generate_flashcards(
        request.content, request.topic, request.count
    )


class QuizGenerateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=16000)
    topic: str = Field("", max_length=200)
    count: int = Field(5, ge=1, le=15)


@app.post("/v1/generate/quiz", dependencies=[Depends(require_api_key)])
async def generate_quiz(request: QuizGenerateRequest):
    """Draft MCQs from lesson content for instructor review. Returns
    {questions: [{text, options, correct_option_index}], engine}."""
    await require_flag("quiz_generation")
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content is required.")
    return await quizgen.generate_quiz(request.content, request.topic, request.count)


class TutorAnswerRequest(BaseModel):
    # bounded so one giant question can't hog retrieval/LLM time
    question: str = Field(..., max_length=4000)
    subject: str = ""
    level: str = ""
    history: list[dict] = []


@app.post("/v1/tutor/answer", dependencies=[Depends(require_api_key)])
async def tutor_answer(request: TutorAnswerRequest):
    """Custom tutor serving: real mark-scheme answers from the aligned
    past-paper corpus, with an optional self-hosted fine-tuned model for
    questions outside it. The Django tutor app points TUTOR_MODEL_URL here."""
    await require_flag("ai_tutor")
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required.")
    return await answering.answer_question(question, request.subject, request.level, history=request.history)
