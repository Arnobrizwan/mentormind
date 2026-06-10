#!/usr/bin/env python3
"""Fetch open science Q&A with worked explanations for the tutor.

Adds long-form physics / chemistry / biology reasoning — the gap the
CAIE mark-scheme corpus (short, terse) and GSM8K/SciQ (maths + one-line
science) don't cover. Each row is a topic-tagged question with a
detailed worked answer, written to data/extra_science.jsonl in the same
chat format as export_dataset.py.

Source: camel-ai/{physics,chemistry,biology} on the Hugging Face
datasets-server. LICENCE: CC-BY-NC-4.0 (non-commercial) — keep this file
SEPARATE from the MIT-licensed corpus so it can be excluded from a
commercial fine-tune. Train with:
    python scripts/train_tutor.py --extra data/supplementary.jsonl \
                                          data/extra_science.jsonl

Usage:
    python scripts/fetch_science.py                # 8000 rows / subject
    python scripts/fetch_science.py --limit 4000   # smaller, faster
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://datasets-server.huggingface.co/rows"
OUT = Path(__file__).resolve().parent.parent / "data" / "extra_science.jsonl"
PAGE = 100

# (dataset, subject label, system prompt)
SOURCES = [
    ("camel-ai/physics", "Physics", "Physics tutor. Explain with formulae, derivations and units."),
    ("camel-ai/chemistry", "Chemistry", "Chemistry tutor. Explain with equations, mechanisms and reasoning."),
    ("camel-ai/biology", "Biology", "Biology tutor. Explain clearly with labelled reasoning."),
]


def rows(dataset: str, limit: int):
    offset = 0
    while offset < limit:
        length = min(PAGE, limit - offset)
        query = urllib.parse.urlencode(
            {"dataset": dataset, "config": "default", "split": "train",
             "offset": offset, "length": length}
        )
        request = urllib.request.Request(
            f"{API}?{query}", headers={"User-Agent": "Mozilla/5.0"}
        )
        payload = None
        for attempt in range(8):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    retry_after = exc.headers.get("Retry-After")
                    wait = int(retry_after) if (retry_after or "").isdigit() else 0
                    time.sleep(max(wait, 15 * (attempt + 1)))
                elif attempt == 7:
                    raise
                else:
                    time.sleep(2 * (attempt + 1))
            except Exception:
                if attempt == 7:
                    raise
                time.sleep(2 * (attempt + 1))
        if payload is None:
            raise SystemExit("datasets-server kept rate-limiting — try again later")
        batch = payload.get("rows", [])
        if not batch:
            return
        for item in batch:
            yield item["row"]
        offset += len(batch)
        time.sleep(1.0)


def record(row: dict, subject: str, system: str) -> dict | None:
    question = (row.get("message_1") or "").strip()
    answer = (row.get("message_2") or "").strip()
    if len(question) < 25 or len(answer) < 25:
        return None
    sub_topic = (row.get("sub_topic") or "").strip()
    sys_prompt = f"{system}" + (f" Topic: {sub_topic}." if sub_topic else "")
    return {
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=8000, help="Rows per subject")
    args = parser.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as fh:
        for dataset, subject, system in SOURCES:
            count = 0
            for row in rows(dataset, args.limit):
                item = record(row, subject, system)
                if item is None:
                    continue
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
                count += 1
            written += count
            print(f"{dataset}: {count} examples", flush=True)

    print(f"\nWrote {written} science examples to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
