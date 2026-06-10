"""REST surface for the past-paper training pipeline."""

from __future__ import annotations

import hmac
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from . import models
from .models import AlignedQuestion, PastPaper
from .processor import CambridgePipelineProcessor

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

DEFAULT_SYSTEM_PROMPT = os.getenv(
    "PASTPAPERS_SYSTEM_PROMPT",
    "You are an expert Cambridge O/A Level tutor. Answer exam questions "
    "with full step-by-step working exactly as a mark scheme would award it.",
)

_DEFAULT_PAPERS_ROOT = str(Path(__file__).resolve().parent.parent.parent / "data" / "papers")


def papers_root() -> Path:
    """Folder scans are confined to this root — a request can't walk outside
    it. Resolved per call so deployments (and tests) can repoint it via
    PASTPAPERS_ROOT."""
    return Path(os.getenv("PASTPAPERS_ROOT", _DEFAULT_PAPERS_ROOT)).resolve()


def require_pipeline_token(x_pipeline_token: str = Header(default="")) -> None:
    """Admin-only mutating endpoints. When PIPELINE_API_TOKEN is set, callers
    must present it; left unset in local dev so the pipeline stays scriptable."""
    token = os.getenv("PIPELINE_API_TOKEN", "")
    if token and not hmac.compare_digest(x_pipeline_token, token):
        raise HTTPException(status_code=401, detail="Invalid or missing pipeline token.")


def _safe_folder(folder: str) -> str:
    """Resolve `folder` and refuse anything outside the papers root."""
    root = papers_root()
    candidate = (
        Path(folder).resolve()
        if Path(folder).is_absolute()
        else (root / folder).resolve()
    )
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="folder must be within the papers root.")
    return str(candidate)


processor = CambridgePipelineProcessor()


class DiscoverRequest(BaseModel):
    folder: str = Field(..., description="Local folder to scan recursively for CAIE PDFs")


class DiscoverResponse(BaseModel):
    matched_pdfs: int
    created: int
    skipped_files: int


class ProcessResponse(BaseModel):
    processed: bool
    paper: str | None = None
    aligned_questions: int | None = None
    detail: str | None = None


@router.post("/discover", response_model=DiscoverResponse)
async def discover(
    request: DiscoverRequest, _: None = Depends(require_pipeline_token)
) -> DiscoverResponse:
    """Scan a local folder, seed the DB with QP/MS rows set to PENDING."""
    try:
        result = await processor.discover(_safe_folder(request.folder))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return DiscoverResponse(**result)


@router.post("/process-next", response_model=ProcessResponse)
async def process_next(_: None = Depends(require_pipeline_token)) -> ProcessResponse:
    """OCR + align the next available QP/MS pair and mark it ALIGNED."""
    pair = await processor.find_next_pair()
    if pair is None:
        return ProcessResponse(processed=False, detail="No unaligned QP/MS pairs left.")
    qp, ms = pair
    try:
        result = await processor.process_pair(qp, ms)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {exc}")
    return ProcessResponse(processed=True, **result)


@router.get("/dataset")
async def dataset(subject_code: str | None = None, limit: int = 1000) -> dict:
    """The aligned corpus as a chat-format training dataset.

    Each item is one conversation:
    {"messages": [{role: system}, {role: user = question},
                  {role: assistant = mark scheme}]}
    """
    async with models.SessionFactory() as session:
        query = (
            select(AlignedQuestion, PastPaper)
            .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
            .order_by(PastPaper.subject_code, PastPaper.year, AlignedQuestion.question_number)
            .limit(max(1, min(limit, 10_000)))
        )
        if subject_code:
            query = query.where(PastPaper.subject_code == subject_code)
        rows = (await session.execute(query)).all()

        total = await session.scalar(select(func.count(AlignedQuestion.id)))

    return {
        "count": len(rows),
        "total_available": total or 0,
        "data": [
            {
                "messages": [
                    {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": question.question_markdown},
                    {"role": "assistant", "content": question.mark_scheme_markdown},
                ],
                "meta": {
                    "subject_code": paper.subject_code,
                    "year": paper.year,
                    "session": paper.session,
                    "variant": paper.paper_variant,
                    "question_number": question.question_number,
                },
            }
            for question, paper in rows
        ],
    }
