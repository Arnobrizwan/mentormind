"""MCQ quiz generation from lesson content.

Engine chain (same pattern as grading/flashcards):
1. **Fine-tuned LLM** (LOCAL_LLM=1 in-process, or CUSTOM_LLM_URL) prompted
   to emit a JSON array of MCQs.
2. **Heuristic fallback** — definition-shaped lines become "which best
   describes X?" questions with the other definitions as distractors.

Output is a *draft*: the Django side returns it to the instructor for
review and editing — nothing is auto-published to students.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re

import httpx

from .llm_json import extract_array
from .pastpapers import local_llm
from .pastpapers.answering import _allowed_llm_url

logger = logging.getLogger(__name__)

CUSTOM_LLM_TIMEOUT = float(os.getenv("CUSTOM_LLM_TIMEOUT", "30"))

# Same separators as flashcards.py: colon, em/en dash, whitespace-flanked
# hyphen — hyphenated terms like "Self-inductance" stay intact.
_DEFINITION_RE = re.compile(r"^\s*[\-\*•]?\s*([^:—–\n]{3,80}?)\s*(?::|[—–]|\s-)\s+(.{8,})$")
_MD_NOISE_RE = re.compile(r"[#*_`>]+")


def _generation_prompt(topic: str, count: int) -> str:
    return (
        "You are writing multiple-choice questions for Cambridge exam "
        f"revision on the topic '{topic or 'this lesson'}'.\n"
        f"From the lesson content the user provides, write up to {count} "
        "MCQs. Each has exactly 4 options with one correct answer and "
        "plausible distractors.\n"
        "Respond with ONLY a JSON array — no prose, no markdown fences:\n"
        '[{"text": "...", "options": ["...", "...", "...", "..."], '
        '"correct_option_index": 0}, ...]'
    )


def _parse_llm_questions(raw: str, count: int) -> list[dict] | None:
    body = extract_array(raw)
    if body is None:
        return None
    questions = []
    for item in body:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        options = item.get("options")
        index = item.get("correct_option_index")
        if (
            not text
            or not isinstance(options, list)
            or not 2 <= len(options) <= 6
            or not all(isinstance(o, str) and o.strip() for o in options)
            or not isinstance(index, int)
            or not 0 <= index < len(options)
        ):
            continue
        questions.append(
            {
                "text": text[:1000],
                "options": [str(o).strip()[:300] for o in options],
                "correct_option_index": index,
            }
        )
    return questions[:count] or None


def _heuristic_questions(content: str, topic: str, count: int) -> list[dict]:
    """No-model fallback: each definition line becomes a 'which best
    describes X?' MCQ, with the other definitions as distractors."""
    pairs = []
    for line in content.splitlines():
        match = _DEFINITION_RE.match(_MD_NOISE_RE.sub("", line))
        if match:
            pairs.append((match.group(1).strip(), match.group(2).strip()))
    if len(pairs) < 2:
        return []  # not enough material for credible distractors

    rng = random.Random(len(content))  # deterministic for a given lesson
    questions = []
    for term, meaning in pairs[:count]:
        # A distractor identical to the answer would make two options
        # "correct" while only one index is marked — drop duplicates.
        distractors = list({m for t, m in pairs if t != term and m != meaning})
        if not distractors:
            continue
        rng.shuffle(distractors)
        options = distractors[:3] + [meaning]
        rng.shuffle(options)
        questions.append(
            {
                "text": f"Which of the following best describes {term}?",
                "options": [o[:300] for o in options],
                "correct_option_index": options.index(meaning),
            }
        )
    return questions


async def _llm_questions_text(content: str, topic: str, count: int) -> str | None:
    system = _generation_prompt(topic, count)
    local = await asyncio.to_thread(local_llm.generate, content, system)
    if local:
        return local

    url = os.getenv("CUSTOM_LLM_URL", "")
    if not url or not _allowed_llm_url(url):
        return None
    payload = {
        "model": os.getenv("CUSTOM_LLM_MODEL", "mentormind-tutor"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        "temperature": 0.3,
    }
    try:
        async with httpx.AsyncClient(timeout=CUSTOM_LLM_TIMEOUT) as client:
            response = await client.post(url.rstrip("/") + "/v1/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


async def generate_quiz(content: str, topic: str, count: int) -> dict:
    """Always returns {questions: [...], engine: 'llm'|'heuristic'} —
    questions may be empty if the content has nothing extractable."""
    raw = await _llm_questions_text(content, topic, count)
    if raw:
        questions = _parse_llm_questions(raw, count)
        if questions:
            return {"questions": questions, "engine": "llm"}
        logger.warning("LLM quiz reply was not valid JSON — using heuristic")
    return {
        "questions": _heuristic_questions(content, topic, count),
        "engine": "heuristic",
    }
