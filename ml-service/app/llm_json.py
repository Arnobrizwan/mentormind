"""Robust JSON extraction from LLM replies.

Models wrap JSON in prose, fences, or emit trailing junk. A greedy
first-to-last-bracket regex breaks the moment a second brace appears
after the payload — instead, scan for each candidate opener and let the
JSON decoder find the real end of the value (raw_decode). Replies are a
few KB, so the worst-case rescan is irrelevant.
"""

from __future__ import annotations

import json

_decoder = json.JSONDecoder()


def _extract(raw: str, opener: str, kind: type) -> object | None:
    for position, char in enumerate(raw):
        if char != opener:
            continue
        try:
            value, _ = _decoder.raw_decode(raw[position:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, kind):
            return value
    return None


def extract_object(raw: str) -> dict | None:
    """First parseable JSON object in the text, or None."""
    return _extract(raw, "{", dict)


def extract_array(raw: str) -> list | None:
    """First parseable JSON array in the text, or None."""
    return _extract(raw, "[", list)
