"""Flashcard generation from lesson content.

Engine chain (same pattern as grading):
1. **Fine-tuned LLM** (LOCAL_LLM=1 in-process, or CUSTOM_LLM_URL) prompted
   to emit a JSON array of {front, back} cards.
2. **Heuristic fallback** — definition-style lines ("Term: meaning",
   "Term — meaning") and key sentences become cloze-ish cards, so the
   feature still works with no model loaded.

Cards are drafts: the Django side files them unpublished for instructor
review — nothing generated here reaches a student unapproved.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import httpx

from .pastpapers import local_llm
from .pastpapers.answering import _allowed_llm_url

logger = logging.getLogger(__name__)

CUSTOM_LLM_TIMEOUT = float(os.getenv("CUSTOM_LLM_TIMEOUT", "30"))

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)
# "Term: definition" / "Term — definition" / "Term - definition"
_DEFINITION_RE = re.compile(r"^\s*[\-\*•]?\s*([^:—\-\n]{3,80})\s*[:—]\s+(.{8,})$")
_MD_NOISE_RE = re.compile(r"[#*_`>]+")


def _generation_prompt(topic: str, count: int) -> str:
    return (
        "You are creating spaced-repetition flashcards for Cambridge exam "
        f"revision on the topic '{topic or 'this lesson'}'.\n"
        f"From the lesson content the user provides, write up to {count} "
        "flashcards testing the most examinable facts, definitions and "
        "methods. Fronts are short questions or cues; backs are concise, "
        "precise answers.\n"
        "Respond with ONLY a JSON array — no prose, no markdown fences:\n"
        '[{"front": "...", "back": "..."}, ...]'
    )


def _parse_llm_cards(raw: str, count: int) -> list[dict] | None:
    match = _JSON_ARRAY_RE.search(raw)
    if not match:
        return None
    try:
        body = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(body, list):
        return None
    cards = []
    for item in body:
        if not isinstance(item, dict):
            continue
        front = str(item.get("front", "")).strip()
        back = str(item.get("back", "")).strip()
        if front and back:
            cards.append({"front": front[:500], "back": back[:1000]})
    return cards[:count] or None


def _heuristic_cards(content: str, topic: str, count: int) -> list[dict]:
    """No-model fallback: mine definition-shaped lines first, then turn the
    longest informative sentences into recall prompts."""
    cards: list[dict] = []
    seen: set[str] = set()

    for line in content.splitlines():
        match = _DEFINITION_RE.match(_MD_NOISE_RE.sub("", line))
        if not match:
            continue
        term, meaning = match.group(1).strip(), match.group(2).strip()
        if term.lower() in seen:
            continue
        seen.add(term.lower())
        cards.append({"front": f"What is {term}?", "back": meaning[:1000]})
        if len(cards) >= count:
            return cards

    plain = _MD_NOISE_RE.sub("", content)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if len(s.strip()) > 60]
    sentences.sort(key=len, reverse=True)
    for sentence in sentences:
        if len(cards) >= count:
            break
        opening = " ".join(sentence.split()[:6])
        cards.append(
            {
                "front": f"Recall the key point about: “{opening}…” "
                f"({topic})" if topic else f"Recall: “{opening}…”",
                "back": sentence[:1000],
            }
        )
    return cards


async def _llm_cards_text(content: str, topic: str, count: int) -> str | None:
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


async def generate_flashcards(content: str, topic: str, count: int) -> dict:
    """Always returns {cards: [...], engine: 'llm'|'heuristic'}."""
    raw = await _llm_cards_text(content, topic, count)
    if raw:
        cards = _parse_llm_cards(raw, count)
        if cards:
            return {"cards": cards, "engine": "llm"}
        logger.warning("LLM flashcard reply was not valid JSON — using heuristic")
    return {"cards": _heuristic_cards(content, topic, count), "engine": "heuristic"}
