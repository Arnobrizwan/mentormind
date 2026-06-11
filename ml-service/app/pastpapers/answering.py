"""Custom tutor answering — grounded in real Cambridge mark schemes.

Strategy, in order:
1. **Retrieval (always on).** Score the student's question against every
   aligned QP question in the corpus (token-overlap cosine). A strong
   match returns the *actual mark scheme working* — a textbook answer,
   not a generated one — with full source attribution.
2. **Fine-tuned model (optional).** When CUSTOM_LLM_URL points at an
   OpenAI-compatible server (vLLM/llama.cpp/Ollama) hosting the model
   you fine-tuned on /api/pipeline/dataset, weak/no matches are answered
   by that model, with the nearest mark schemes injected as grounding
   context. If the server is down, retrieval guidance still answers.

No third-party AI APIs are involved anywhere in this path.
"""

from __future__ import annotations

import asyncio
import math
import os
import re

import httpx
from sqlalchemy import select

from . import local_llm, models
from .models import AlignedQuestion, PastPaper

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "the a an of to in and or for is are be was with on at by it this that "
    "find show state give which what how why your you".split()
)

# Retrieval/LLM knobs — env-tunable without a redeploy.
STRONG_MATCH = float(os.getenv("TUTOR_STRONG_MATCH", "0.45"))
WEAK_MATCH = float(os.getenv("TUTOR_WEAK_MATCH", "0.18"))
# Corpus rows scanned per query — plenty for CAIE scale.
MAX_CANDIDATES = int(os.getenv("TUTOR_MAX_CANDIDATES", "5000"))

CUSTOM_LLM_TIMEOUT = float(os.getenv("CUSTOM_LLM_TIMEOUT", "30"))

# Token sets per aligned-question row id, built lazily on first retrieval.
# The corpus is append-mostly and capped at MAX_CANDIDATES rows, so caching
# every row is cheap; the size guard only trips if the DB is swapped out.
_token_cache: dict[int, set[str]] = {}


def _allowed_llm_url(url: str) -> bool:
    """Only http(s) and never a credentialed URL — a defence-in-depth check
    on the operator-set CUSTOM_LLM_URL so a misconfig can't turn the tutor
    into an SSRF primitive against arbitrary schemes."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.hostname) and "@" not in parsed.netloc


def _tokens(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS}


def _similarity(query: set[str], candidate: set[str]) -> float:
    """Cosine-style overlap on token sets — fast, dependency-free, and
    good enough to find 'the same question, reworded'."""
    if not query or not candidate:
        return 0.0
    overlap = len(query & candidate)
    return overlap / math.sqrt(len(query) * len(candidate))


def _source_of(paper: PastPaper, question: AlignedQuestion) -> dict:
    return {
        "subject_code": paper.subject_code,
        "year": paper.year,
        "session": paper.session,
        "variant": paper.paper_variant,
        "question_number": question.question_number,
    }


async def _ranked_matches(
    question_text: str, limit: int = 3, exclude_ids: set[str] | None = None
) -> list[tuple[float, AlignedQuestion, PastPaper]]:
    query = _tokens(question_text)
    statement = (
        select(AlignedQuestion, PastPaper)
        .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
        .limit(MAX_CANDIDATES)
    )
    if exclude_ids:
        # Evaluation harness: a question being scored must not retrieve
        # itself, or held-out accuracy is meaninglessly perfect.
        statement = statement.where(AlignedQuestion.id.notin_(exclude_ids))
    async with models.SessionFactory() as session:
        rows = (await session.execute(statement)).all()
    if len(_token_cache) > 2 * MAX_CANDIDATES:
        _token_cache.clear()  # only on a corpus swap; normal growth never trips this
    scored = []
    for aligned, paper in rows:
        candidate = _token_cache.get(aligned.id)
        if candidate is None:
            candidate = _token_cache[aligned.id] = _tokens(aligned.question_markdown)
        scored.append((_similarity(query, candidate), aligned, paper))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:limit]


def _system_prompt(subject: str, level: str, context: str) -> str:
    return (
        f"You are a Cambridge {level or 'O/A Level'} {subject or ''} tutor. "
        "Answer with full step-by-step working in mark-scheme style. "
        "Ground your answer in this reference material:\n\n" + context
    )


async def _generate_answer(question: str, subject: str, level: str, context: str) -> str | None:
    """Generate from the fine-tuned model. Tries fully-offline in-process
    inference first (LOCAL_LLM=1), then an OpenAI-compatible server
    (CUSTOM_LLM_URL). Returns None if neither is available."""
    # In-process inference is CPU/GPU-bound and takes seconds — run it in a
    # worker thread so it can't stall the event loop.
    local = await asyncio.to_thread(
        local_llm.generate, question, _system_prompt(subject, level, ""), context
    )
    if local:
        return local

    url = os.getenv("CUSTOM_LLM_URL", "")
    if not url or not _allowed_llm_url(url):
        return None
    payload = {
        "model": os.getenv("CUSTOM_LLM_MODEL", "mentormind-tutor"),
        "messages": [
            {"role": "system", "content": _system_prompt(subject, level, context)},
            {"role": "user", "content": question},
        ],
        "temperature": 0.2,
    }
    try:
        # async client — a slow LLM server must not block the event loop
        async with httpx.AsyncClient(timeout=CUSTOM_LLM_TIMEOUT) as client:
            response = await client.post(
                url.rstrip("/") + "/v1/chat/completions", json=payload
            )
            response.raise_for_status()
            body = response.json()
        return body["choices"][0]["message"]["content"]
    except Exception:
        return None


async def answer_question(
    question: str,
    subject: str = "",
    level: str = "",
    exclude_ids: set[str] | None = None,
) -> dict:
    """Answer a student's question from the past-paper corpus.

    Returns {"answer": str, "matched": bool, "source": dict | None}.
    exclude_ids is for the evaluation harness only (leave-one-out).
    """
    matches = await _ranked_matches(question, exclude_ids=exclude_ids)
    best = matches[0] if matches else None

    # 1) Strong match — return the real mark-scheme working verbatim.
    if best and best[0] >= STRONG_MATCH:
        score, aligned, paper = best
        answer = (
            "Here is the official mark-scheme working for this question:\n\n"
            f"**Question** (as set):\n\n{aligned.question_markdown}\n\n"
            f"**Step-by-step solution:**\n\n{aligned.mark_scheme_markdown}"
        )
        return {"answer": answer, "matched": True, "source": _source_of(paper, aligned)}

    # 2) Weak/no match — try the fine-tuned model with retrieved grounding.
    context = "\n\n---\n\n".join(
        f"Q: {aligned.question_markdown}\nMark scheme: {aligned.mark_scheme_markdown}"
        for score, aligned, paper in matches
        if score >= WEAK_MATCH
    )
    generated = await _generate_answer(question, subject, level, context)
    if generated:
        source = _source_of(matches[0][2], matches[0][1]) if context else None
        return {"answer": generated, "matched": False, "source": source}

    # 3) Retrieval guidance from the nearest mark scheme.
    if best and best[0] >= WEAK_MATCH:
        score, aligned, paper = best
        answer = (
            "I couldn't find this exact question in the corpus, but here is "
            "the closest past-paper question and its mark scheme — the same "
            "method applies:\n\n"
            f"**Similar question:**\n\n{aligned.question_markdown}\n\n"
            f"**Mark-scheme method:**\n\n{aligned.mark_scheme_markdown}"
        )
        return {"answer": answer, "matched": False, "source": _source_of(paper, aligned)}

    # 4) Nothing useful in the corpus yet.
    return {
        "answer": (
            "This question isn't covered by the aligned past-paper corpus yet. "
            "Run more papers through the pipeline (POST /api/pipeline/process-next) "
            "to expand coverage, then ask again."
        ),
        "matched": False,
        "source": None,
    }
