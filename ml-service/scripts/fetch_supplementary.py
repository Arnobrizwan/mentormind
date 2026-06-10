#!/usr/bin/env python3
"""Fetch open supplementary training datasets for the tutor.

The past-paper corpus teaches mark-scheme style; these add general
reasoning breadth so the fine-tune generalises beyond CAIE phrasing:

- GSM8K (openai/gsm8k, MIT): grade-school maths word problems with
  step-by-step worked solutions.
- SciQ (allenai/sciq, CC BY-NC 3.0): science questions with a one-line
  answer and a supporting explanation.

Rows are streamed from the Hugging Face datasets-server (plain JSON,
no extra dependencies) and written to data/supplementary.jsonl in the
same chat format as export_dataset.py, so train_tutor.py can merge
them with --extra.

Usage:
    python scripts/fetch_supplementary.py                # both datasets
    python scripts/fetch_supplementary.py --limit 2000   # cap per dataset
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://datasets-server.huggingface.co/rows"
OUT = Path(__file__).resolve().parent.parent / "data" / "supplementary.jsonl"
PAGE = 100

MATHS_SYSTEM = "Mathematics tutor. Show full step-by-step working."
SCIENCE_SYSTEM = "Science tutor. Answer in clear points with a short explanation."


def rows(dataset: str, config: str, split: str, limit: int | None):
    offset = 0
    while True:
        query = urllib.parse.urlencode(
            {
                "dataset": dataset,
                "config": config,
                "split": split,
                "offset": offset,
                "length": PAGE,
            }
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
                if exc.code == 429:  # rate-limited — back off hard and retry
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
            offset += 1
            if limit and offset >= limit:
                return
        time.sleep(1.0)


def gsm8k_record(row: dict) -> dict | None:
    question = (row.get("question") or "").strip()
    answer = (row.get("answer") or "").strip()
    if not question or not answer:
        return None
    # "#### 42" terminator → a readable final-answer line.
    answer = answer.replace("####", "Answer:").strip()
    return {
        "messages": [
            {"role": "system", "content": MATHS_SYSTEM},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
    }


def sciq_record(row: dict) -> dict | None:
    question = (row.get("question") or "").strip()
    answer = (row.get("correct_answer") or "").strip()
    support = (row.get("support") or "").strip()
    if not question or not answer:
        return None
    body = f"{support}\n\nAnswer: {answer}" if support else f"Answer: {answer}"
    return {
        "messages": [
            {"role": "system", "content": SCIENCE_SYSTEM},
            {"role": "user", "content": question},
            {"role": "assistant", "content": body.strip()},
        ]
    }


SOURCES = [
    ("openai/gsm8k", "main", "train", gsm8k_record),
    ("allenai/sciq", "default", "train", sciq_record),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Cap rows per dataset")
    args = parser.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as fh:
        for dataset, config, split, convert in SOURCES:
            count = 0
            for row in rows(dataset, config, split, args.limit):
                record = convert(row)
                if record is None:
                    continue
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
            written += count
            print(f"{dataset}: {count} examples", flush=True)

    print(f"\nWrote {written} supplementary examples to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
