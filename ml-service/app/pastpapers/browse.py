"""Read-only browse surface for the aligned past-paper corpus.

Serves the frontend's paper-browser: subject aggregates, paginated
question lists (sans mark schemes), single-question detail, and random
samples. Queries follow the async session pattern from api.py — the
models module is imported (not the symbol) so tests can repoint
SessionFactory.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from . import models
from .models import AlignedQuestion, PastPaper

router = APIRouter(prefix="/v1/papers", tags=["papers"])


def _question_fields(question: AlignedQuestion, paper: PastPaper) -> dict:
    """List-view shape: everything but the mark scheme."""
    return {
        "id": question.id,
        "subject_code": paper.subject_code,
        "year": paper.year,
        "session": paper.session,
        "variant": paper.paper_variant,
        "question_number": question.question_number,
        "question_markdown": question.question_markdown,
    }


def _full_question(question: AlignedQuestion, paper: PastPaper) -> dict:
    """Detail shape: list fields plus the mark scheme."""
    return {
        **_question_fields(question, paper),
        "mark_scheme_markdown": question.mark_scheme_markdown,
    }


@router.get("/subjects")
async def subjects() -> dict:
    """Subjects in the corpus with their aligned-question counts."""
    async with models.SessionFactory() as session:
        query = (
            select(PastPaper.subject_code, func.count(AlignedQuestion.id))
            .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
            .group_by(PastPaper.subject_code)
            .order_by(func.count(AlignedQuestion.id).desc())
        )
        rows = (await session.execute(query)).all()
    return {
        "subjects": [
            {"subject_code": code, "questions": count} for code, count in rows
        ]
    }


@router.get("/questions")
async def list_questions(
    subject_code: str | None = None, page: int = 1, page_size: int = 20
) -> dict:
    """Paginated question list — no mark schemes in the list view."""
    page = max(1, page)
    page_size = max(1, min(page_size, 50))

    async with models.SessionFactory() as session:
        count_query = select(func.count(AlignedQuestion.id)).join(
            PastPaper, AlignedQuestion.question_paper_id == PastPaper.id
        )
        query = (
            select(AlignedQuestion, PastPaper)
            .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
            .order_by(
                PastPaper.year.desc(),
                PastPaper.paper_variant,
                AlignedQuestion.question_number,
            )
        )
        if subject_code:
            count_query = count_query.where(PastPaper.subject_code == subject_code)
            query = query.where(PastPaper.subject_code == subject_code)

        total = await session.scalar(count_query)
        rows = (
            await session.execute(
                query.offset((page - 1) * page_size).limit(page_size)
            )
        ).all()

    return {
        "count": total or 0,
        "page": page,
        "results": [_question_fields(question, paper) for question, paper in rows],
    }


@router.get("/questions/{question_id}")
async def question_detail(question_id: str) -> dict:
    """A single aligned question, mark scheme included."""
    async with models.SessionFactory() as session:
        query = (
            select(AlignedQuestion, PastPaper)
            .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
            .where(AlignedQuestion.id == question_id)
        )
        row = (await session.execute(query)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Question not found.")
    question, paper = row
    return _full_question(question, paper)


@router.get("/sample")
async def sample(subject_code: str | None = None, count: int = 10) -> dict:
    """A random sample of full questions (mark schemes included)."""
    count = max(1, min(count, 20))
    async with models.SessionFactory() as session:
        query = (
            select(AlignedQuestion, PastPaper)
            .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
            .order_by(func.random())
            .limit(count)
        )
        if subject_code:
            query = query.where(PastPaper.subject_code == subject_code)
        rows = (await session.execute(query)).all()
    return {
        "questions": [_full_question(question, paper) for question, paper in rows]
    }
