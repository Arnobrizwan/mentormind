"""Database layer for the Cambridge past-paper training pipeline.

SQLAlchemy 2.0 async ORM. The engine URL is environment-driven:
PASTPAPERS_DB_URL (default: a local SQLite file via aiosqlite), so the
same code runs against Postgres in production
(postgresql+asyncpg://...) without changes.
"""

from __future__ import annotations

import enum
import os
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DB_URL = os.getenv("PASTPAPERS_DB_URL", "sqlite+aiosqlite:///./pastpapers.db")

engine = create_async_engine(DB_URL, echo=False)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class PaperStatus(str, enum.Enum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    OCR_PROCESSING = "OCR_PROCESSING"
    OCR_COMPLETED = "OCR_COMPLETED"
    ALIGNED = "ALIGNED"
    FAILED = "FAILED"


class DocumentType(str, enum.Enum):
    QP = "QP"  # Question Paper
    MS = "MS"  # Mark Scheme


class PastPaper(Base):
    """One Cambridge document (a question paper or its mark scheme)."""

    __tablename__ = "past_papers"
    __table_args__ = (
        UniqueConstraint(
            "subject_code", "year", "session", "paper_variant", "document_type",
            name="uq_paper_identity",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    subject_code: Mapped[str] = mapped_column(String(8), index=True)
    year: Mapped[int] = mapped_column(Integer)
    session: Mapped[str] = mapped_column(String(1))  # s / w / m
    paper_variant: Mapped[str] = mapped_column(String(4))
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    raw_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_markdown_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[PaperStatus] = mapped_column(
        Enum(PaperStatus), default=PaperStatus.PENDING, index=True
    )
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    aligned_questions: Mapped[list["AlignedQuestion"]] = relationship(
        back_populates="question_paper",
        cascade="all, delete-orphan",
        foreign_keys="AlignedQuestion.question_paper_id",
    )

    def label(self) -> str:
        return (
            f"{self.subject_code}_{self.session}{str(self.year)[-2:]}"
            f"_{self.document_type.value.lower()}_{self.paper_variant}"
        )


class AlignedQuestion(Base):
    """A QP question matched to its MS mark allocation — one training row."""

    __tablename__ = "aligned_questions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question_paper_id: Mapped[str] = mapped_column(
        ForeignKey("past_papers.id"), index=True
    )
    question_number: Mapped[int] = mapped_column(Integer)
    question_markdown: Mapped[str] = mapped_column(Text)
    mark_scheme_markdown: Mapped[str] = mapped_column(Text)

    question_paper: Mapped[PastPaper] = relationship(
        back_populates="aligned_questions", foreign_keys=[question_paper_id]
    )


async def init_db() -> None:
    """Create tables if missing — call once at application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    return SessionFactory()
