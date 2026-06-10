"""Cambridge past-paper pipeline: discovery → OCR → QP/MS alignment.

Filename convention (standard CAIE naming):
    <subject>_<session><yy>_<qp|ms>_<variant>.pdf
    e.g.  9709_s23_qp_12.pdf   pairs with   9709_s23_ms_12.pdf
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from . import models
from .models import AlignedQuestion, DocumentType, PaperStatus, PastPaper
from .ocr import MistralOCRService, OCRServiceError

logger = logging.getLogger(__name__)

FILENAME_RE = re.compile(
    r"^(?P<subject>\d{4})_(?P<session>[swm])(?P<year>\d{2})"
    r"_(?P<type>qp|ms)_(?P<variant>\d{1,2})\.pdf$",
    re.IGNORECASE,
)

# A question starts at the beginning of a line as a bare/bold/heading
# number: "1 ", "**3** ", "# 7", "12." etc.
QUESTION_START_RE = re.compile(
    r"^(?:#{1,3}\s*)?(?:\*\*)?(\d{1,2})(?:\*\*)?[.)]?\s+",
    re.MULTILINE,
)

MARKDOWN_DIR = os.getenv("PASTPAPERS_MARKDOWN_DIR", "")


@dataclass(frozen=True)
class ParsedFilename:
    subject_code: str
    year: int
    session: str
    paper_variant: str
    document_type: DocumentType


def parse_filename(name: str) -> ParsedFilename | None:
    """Decode a CAIE filename; None when it doesn't match the convention."""
    match = FILENAME_RE.match(name)
    if not match:
        return None
    return ParsedFilename(
        subject_code=match["subject"],
        year=2000 + int(match["year"]),
        session=match["session"].lower(),
        paper_variant=match["variant"],
        document_type=DocumentType(match["type"].upper()),
    )


def split_questions(markdown: str) -> dict[int, str]:
    """Split a paper's Markdown into {question_number: block}.

    Question starts must form a strictly increasing sequence beginning at
    1 — that filters out stray line-leading numbers (years, marks, data
    values) that would otherwise look like question starts.
    """
    candidates = [
        (m.start(), int(m.group(1))) for m in QUESTION_START_RE.finditer(markdown)
    ]
    starts: list[tuple[int, int]] = []
    expected = 1
    for position, number in candidates:
        if number == expected:
            starts.append((position, number))
            expected += 1

    blocks: dict[int, str] = {}
    for index, (position, number) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(markdown)
        block = markdown[position:end].strip()
        # drop page-break rules the OCR pass stitched in
        block = re.sub(r"\n+---\n+", "\n\n", block).strip()
        if block:
            blocks[number] = block
    return blocks


def align_questions(qp_markdown: str, ms_markdown: str) -> list[dict]:
    """Match QP questions to MS allocations by question number."""
    questions = split_questions(qp_markdown)
    schemes = split_questions(ms_markdown)
    return [
        {
            "question_number": number,
            "question": questions[number],
            "mark_scheme": schemes[number],
        }
        for number in sorted(questions)
        if number in schemes
    ]


class CambridgePipelineProcessor:
    """Orchestrates the discover → OCR → align pipeline."""

    def __init__(self, ocr_service: MistralOCRService | None = None) -> None:
        self.ocr = ocr_service or MistralOCRService()

    # -- discovery -----------------------------------------------------------

    async def discover(self, folder: str) -> dict:
        """Scan a folder tree, seed PastPaper rows as PENDING.

        Existing rows are left untouched (idempotent re-scans).
        """
        root = Path(folder)
        if not root.is_dir():
            raise FileNotFoundError(f"Not a directory: {folder}")

        found = skipped = created = 0
        async with models.SessionFactory() as session:
            for pdf in sorted(root.rglob("*.pdf")):
                parsed = parse_filename(pdf.name)
                if parsed is None:
                    skipped += 1
                    continue
                found += 1
                existing = await session.scalar(
                    select(PastPaper).where(
                        PastPaper.subject_code == parsed.subject_code,
                        PastPaper.year == parsed.year,
                        PastPaper.session == parsed.session,
                        PastPaper.paper_variant == parsed.paper_variant,
                        PastPaper.document_type == parsed.document_type,
                    )
                )
                if existing:
                    continue
                session.add(
                    PastPaper(
                        subject_code=parsed.subject_code,
                        year=parsed.year,
                        session=parsed.session,
                        paper_variant=parsed.paper_variant,
                        document_type=parsed.document_type,
                        raw_pdf_path=str(pdf),
                        status=PaperStatus.PENDING,
                    )
                )
                created += 1
            await session.commit()
        return {"matched_pdfs": found, "created": created, "skipped_files": skipped}

    # -- pairing -------------------------------------------------------------

    async def find_next_pair(self) -> tuple[PastPaper, PastPaper] | None:
        """The next QP whose matching MS exists and isn't ALIGNED yet."""
        async with models.SessionFactory() as session:
            qps = (
                await session.scalars(
                    select(PastPaper)
                    .where(
                        PastPaper.document_type == DocumentType.QP,
                        PastPaper.status.notin_(
                            [PaperStatus.ALIGNED, PaperStatus.FAILED]
                        ),
                    )
                    .order_by(PastPaper.created_at)
                )
            ).all()
            for qp in qps:
                ms = await session.scalar(
                    select(PastPaper).where(
                        PastPaper.document_type == DocumentType.MS,
                        PastPaper.subject_code == qp.subject_code,
                        PastPaper.year == qp.year,
                        PastPaper.session == qp.session,
                        PastPaper.paper_variant == qp.paper_variant,
                        PastPaper.status != PaperStatus.FAILED,
                    )
                )
                if ms is not None:
                    return qp, ms
        return None

    # -- processing ----------------------------------------------------------

    @staticmethod
    def _markdown_path(paper: PastPaper) -> Path:
        if MARKDOWN_DIR:
            out_dir = Path(MARKDOWN_DIR)
            out_dir.mkdir(parents=True, exist_ok=True)
            return out_dir / f"{paper.label()}.md"
        return Path(paper.raw_pdf_path or paper.label()).with_suffix(".md")

    async def _set_status(self, paper_ids: list[str], status: PaperStatus, error: str | None = None) -> None:
        async with models.SessionFactory() as session:
            for paper_id in paper_ids:
                paper = await session.get(PastPaper, paper_id)
                if paper:
                    paper.status = status
                    if error:
                        paper.error_log = (paper.error_log or "") + error + "\n"
            await session.commit()

    async def process_pair(self, qp: PastPaper, ms: PastPaper) -> dict:
        """OCR both documents concurrently, align questions, persist rows.

        State machine per the spec:
        DOWNLOADED/PENDING → OCR_PROCESSING → OCR_COMPLETED → ALIGNED
        (FAILED + error_log on any exception).
        """
        ids = [qp.id, ms.id]
        await self._set_status(ids, PaperStatus.OCR_PROCESSING)
        try:
            qp_markdown, ms_markdown = await asyncio.gather(
                self.ocr.process_pdf_to_markdown(qp.raw_pdf_path),
                self.ocr.process_pdf_to_markdown(ms.raw_pdf_path),
            )
        except OCRServiceError as exc:
            await self._set_status(ids, PaperStatus.FAILED, error=str(exc))
            raise

        aligned = align_questions(qp_markdown, ms_markdown)

        async with models.SessionFactory() as session:
            for paper, markdown in ((qp, qp_markdown), (ms, ms_markdown)):
                row = await session.get(PastPaper, paper.id)
                path = self._markdown_path(paper)
                path.write_text(markdown, encoding="utf-8")
                row.ocr_markdown_path = str(path)
                row.status = PaperStatus.OCR_COMPLETED

            qp_row = await session.get(PastPaper, qp.id)
            for item in aligned:
                session.add(
                    AlignedQuestion(
                        question_paper_id=qp.id,
                        question_number=item["question_number"],
                        question_markdown=item["question"],
                        mark_scheme_markdown=item["mark_scheme"],
                    )
                )
            qp_row.status = PaperStatus.ALIGNED
            ms_row = await session.get(PastPaper, ms.id)
            ms_row.status = PaperStatus.ALIGNED
            await session.commit()

        logger.info("aligned %s: %d questions", qp.label(), len(aligned))
        return {"paper": qp.label(), "aligned_questions": len(aligned)}
