"""Async wrapper around Mistral's OCR API.

Flow (per the official docs): upload the PDF with purpose='ocr', fetch a
signed URL, then run `mistral-ocr-latest` against it. The model returns
per-page Markdown with math as native inline ($...$) and block ($$...$$)
LaTeX, which is exactly the format the training dataset needs.

Retries use native-asyncio exponential backoff with jitter, so transient
429 rate limits and 5xx blips never crash a pipeline run.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
from pathlib import Path

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# pypdf renders unmapped math glyphs as /name tokens — translate the
# common Cambridge typesetting ones back to symbols.
GLYPH_MAP = {
    "/lpar": "(", "/rpar": ")", "/lbracket": "[", "/rbracket": "]",
    "/lbrace": "{", "/rbrace": "}", "/minus": "−", "/plus": "+",
    "/times": "×", "/divide": "÷", "/equal": "=", "/radical": "√",
    "/integral": "∫", "/summation": "Σ", "/pi": "π", "/theta": "θ",
    "/alpha": "α", "/beta": "β", "/lambda": "λ", "/mu": "μ",
    "/omega": "ω", "/degree": "°", "/prime": "′", "/infinity": "∞",
    "/lessequal": "≤", "/greaterequal": "≥", "/notequal": "≠",
    "/arrowright": "→", "/proportional": "∝", "/plusminus": "±",
}

BOILERPLATE_RE = re.compile(
    r"^.*(?:© UCLES|DO NOT WRITE IN THIS MARGIN|This document consists of"
    r"|\[Turn over|BLANK PAGE).*$",
    re.MULTILINE,
)
DOTTED_LINES_RE = re.compile(r"\.{6,}")


class OCRServiceError(Exception):
    """Raised when OCR fails after all retries (non-retryable or exhausted)."""


class MistralOCRService:
    """Converts PDF documents to Markdown via the Mistral OCR API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 5,
        base_delay: float = 1.5,
    ) -> None:
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY", "")
        self.model = model or os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._client = None

    def _client_or_raise(self):
        if not self.api_key:
            raise OCRServiceError(
                "MISTRAL_API_KEY is not configured — set it before running OCR."
            )
        if self._client is None:
            try:
                from mistralai import Mistral
            except ImportError as exc:  # pragma: no cover
                raise OCRServiceError(
                    "The 'mistralai' package is not installed (pip install mistralai)."
                ) from exc
            self._client = Mistral(api_key=self.api_key)
        return self._client

    @staticmethod
    def _status_of(exc: Exception) -> int | None:
        for attr in ("status_code", "status"):
            value = getattr(exc, attr, None)
            if isinstance(value, int):
                return value
        return None

    async def _with_backoff(self, label: str, coro_factory):
        """Run an async API call with exponential backoff + jitter on
        rate limits (429) and transient 5xx errors."""
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return await coro_factory()
            except Exception as exc:  # SDKError carries .status_code
                status = self._status_of(exc)
                if status not in RETRYABLE_STATUS:
                    raise OCRServiceError(f"{label} failed: {exc}") from exc
                last_exc = exc
                delay = self.base_delay * (2**attempt) + random.uniform(0, 0.5)
                logger.warning(
                    "%s hit HTTP %s — retry %d/%d in %.1fs",
                    label, status, attempt + 1, self.max_retries, delay,
                )
                await asyncio.sleep(delay)
        raise OCRServiceError(
            f"{label} failed after {self.max_retries} retries: {last_exc}"
        ) from last_exc

    @staticmethod
    def _clean_extracted(text: str) -> str:
        for glyph, symbol in GLYPH_MAP.items():
            text = text.replace(glyph, symbol)
        text = BOILERPLATE_RE.sub("", text)
        text = DOTTED_LINES_RE.sub("", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def _extract_local(self, path: Path) -> str:
        """Keyless fallback: read the PDF's embedded text layer directly.

        Cambridge papers are digitally typeset, so this recovers the full
        question text without any OCR API. Math comes back as plain
        symbols rather than LaTeX — set MISTRAL_API_KEY for LaTeX-grade
        output.
        """
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise OCRServiceError(
                "No MISTRAL_API_KEY and pypdf is not installed — one of the "
                "two is required."
            ) from exc

        reader = PdfReader(str(path))
        pages = [self._clean_extracted(page.extract_text() or "") for page in reader.pages]
        markdown = "\n\n---\n\n".join(p for p in pages if p)
        if not markdown.strip():
            raise OCRServiceError(
                f"{path.name} has no text layer — a scanned PDF needs the "
                "Mistral OCR path (set MISTRAL_API_KEY)."
            )
        return markdown

    async def process_pdf_to_markdown(self, file_path: str) -> str:
        """Convert a PDF to Markdown text.

        With MISTRAL_API_KEY: full OCR via mistral-ocr-latest (handles
        scans, outputs LaTeX math). Without it: the embedded text layer
        is extracted locally, so the pipeline works completely offline.
        Pages are concatenated with horizontal rules either way.
        """
        path = Path(file_path)
        if not path.exists():
            raise OCRServiceError(f"PDF not found: {file_path}")

        if not self.api_key:
            return await asyncio.to_thread(self._extract_local, path)

        client = self._client_or_raise()

        uploaded = await self._with_backoff(
            f"upload {path.name}",
            lambda: client.files.upload_async(
                file={"file_name": path.name, "content": path.read_bytes()},
                purpose="ocr",
            ),
        )
        signed = await self._with_backoff(
            f"sign {path.name}",
            lambda: client.files.get_signed_url_async(file_id=uploaded.id),
        )
        response = await self._with_backoff(
            f"ocr {path.name}",
            lambda: client.ocr.process_async(
                model=self.model,
                document={"type": "document_url", "document_url": signed.url},
            ),
        )

        pages = getattr(response, "pages", []) or []
        markdown = "\n\n---\n\n".join(page.markdown for page in pages)
        if not markdown.strip():
            raise OCRServiceError(f"OCR returned no text for {path.name}")
        return markdown
