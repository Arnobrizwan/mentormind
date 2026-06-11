"""Rubric-based short-answer grading.

Grades a student's free-text answer against an official mark scheme and
returns a structured, criteria-by-criteria breakdown.

Engine chain (mirrors pastpapers.answering):
1. **Fine-tuned LLM** — the in-process tutor model (LOCAL_LLM=1) or an
   OpenAI-compatible server (CUSTOM_LLM_URL), prompted to emit JSON only.
2. **Heuristic fallback** — token-overlap of the student's answer against
   each mark-scheme criterion. Always available, so grading never 503s
   just because no model is loaded.

No third-party AI APIs anywhere in this path.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import httpx

from .pastpapers import local_llm
from .pastpapers.answering import _allowed_llm_url, _similarity, _tokens

logger = logging.getLogger(__name__)

CUSTOM_LLM_TIMEOUT = float(os.getenv("CUSTOM_LLM_TIMEOUT", "30"))
# A criterion counts as met when the student's answer overlaps it this much.
CRITERION_MATCH = float(os.getenv("GRADER_CRITERION_MATCH", "0.30"))

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _grading_prompt(question: str, mark_scheme: str, max_score: int) -> str:
    return (
        "You are a strict Cambridge examiner grading a student's short answer "
        "against the official mark scheme.\n\n"
        f"Question:\n{question}\n\n"
        f"Mark scheme:\n{mark_scheme}\n\n"
        f"Maximum score: {max_score}\n\n"
        "Respond with ONLY a JSON object — no prose, no markdown fences — "
        "with exactly these keys:\n"
        '{"score": <int 0..max>, "criteria_met": [<strings>], '
        '"criteria_missing": [<strings>], "feedback": "<1-3 sentences of '
        'constructive feedback>"}'
    )


def _criteria_lines(mark_scheme: str) -> list[str]:
    """Split a mark scheme into individual gradeable criteria — one per
    bullet/numbered line, falling back to sentences for prose schemes."""
    lines = [
        re.sub(r"^[\s\-\*•]*(?:\(?\d+[\).]|\(?[a-z]\))?\s*", "", line).strip()
        for line in mark_scheme.splitlines()
    ]
    lines = [line for line in lines if len(line) > 3]
    if len(lines) >= 2:
        return lines
    sentences = [s.strip() for s in re.split(r"(?<=[.;])\s+", mark_scheme) if len(s.strip()) > 3]
    return sentences or [mark_scheme.strip()]


def _heuristic_grade(student_answer: str, mark_scheme: str, max_score: int) -> dict:
    """Dependency-free fallback: token overlap per mark-scheme criterion."""
    answer_tokens = _tokens(student_answer)
    criteria = _criteria_lines(mark_scheme)
    met, missing = [], []
    for criterion in criteria:
        if _similarity(answer_tokens, _tokens(criterion)) >= CRITERION_MATCH:
            met.append(criterion)
        else:
            missing.append(criterion)
    score = round(max_score * len(met) / len(criteria)) if criteria else 0
    if missing:
        feedback = (
            "Your answer covers some of the required points, but the mark "
            "scheme also expects: " + "; ".join(missing[:3]) + "."
        )
    else:
        feedback = "Your answer covers all the points the mark scheme looks for — well done."
    return {
        "score": score,
        "max_score": max_score,
        "criteria_met": met,
        "criteria_missing": missing,
        "feedback": feedback,
        "engine": "heuristic",
    }


def _parse_llm_grade(raw: str, max_score: int) -> dict | None:
    """Pull the JSON object out of the model's reply and normalise it.
    Returns None on anything malformed — the caller falls back."""
    match = _JSON_BLOCK_RE.search(raw)
    if not match:
        return None
    try:
        body = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict):
        return None
    try:
        score = int(body.get("score"))
    except (TypeError, ValueError):
        return None
    met = body.get("criteria_met")
    missing = body.get("criteria_missing")
    if not isinstance(met, list) or not isinstance(missing, list):
        return None
    return {
        "score": max(0, min(score, max_score)),
        "max_score": max_score,
        "criteria_met": [str(c) for c in met],
        "criteria_missing": [str(c) for c in missing],
        "feedback": str(body.get("feedback", "")).strip(),
        "engine": "llm",
    }


async def _llm_grade_text(question: str, student_answer: str, mark_scheme: str, max_score: int) -> str | None:
    """Raw model reply for the grading prompt, or None if no model is up."""
    system = _grading_prompt(question, mark_scheme, max_score)
    local = await asyncio.to_thread(local_llm.generate, student_answer, system)
    if local:
        return local

    url = os.getenv("CUSTOM_LLM_URL", "")
    if not url or not _allowed_llm_url(url):
        return None
    payload = {
        "model": os.getenv("CUSTOM_LLM_MODEL", "mentormind-tutor"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": student_answer},
        ],
        "temperature": 0.0,
    }
    try:
        async with httpx.AsyncClient(timeout=CUSTOM_LLM_TIMEOUT) as client:
            response = await client.post(url.rstrip("/") + "/v1/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


async def grade_short_answer(question: str, student_answer: str, mark_scheme: str, max_score: int) -> dict:
    """Grade an answer. Always returns a result — LLM when available,
    criterion-overlap heuristic otherwise."""
    raw = await _llm_grade_text(question, student_answer, mark_scheme, max_score)
    if raw:
        parsed = _parse_llm_grade(raw, max_score)
        if parsed:
            return parsed
        logger.warning("LLM grade reply was not valid JSON — using heuristic")
    return _heuristic_grade(student_answer, mark_scheme, max_score)
