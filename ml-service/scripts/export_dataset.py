#!/usr/bin/env python3
"""Export the aligned corpus to a chat-format JSONL training file.

Each line is one training conversation:
    {"messages": [{"role": "system", ...},
                  {"role": "user", "content": "<question>"},
                  {"role": "assistant", "content": "<mark scheme>"}]}

This is the exact format consumed by OpenAI-compatible fine-tuners
(Together, Fireworks, Axolotl, Unsloth, LLaMA-Factory, vLLM LoRA).

Usage:
    python scripts/export_dataset.py                 # -> data/dataset.jsonl
    python scripts/export_dataset.py --subject 4024  # one subject only
    python scripts/export_dataset.py --min-chars 40  # drop trivial rows
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.pastpapers import models  # noqa: E402
from app.pastpapers.api import DEFAULT_SYSTEM_PROMPT  # noqa: E402
from app.pastpapers.models import AlignedQuestion, PastPaper  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "dataset.jsonl"

# Subject-aware system prompts keep the tutor in the right voice per
# discipline — driven by syllabus code, no hardcoding in the model.
SUBJECT_PROMPTS = {
    "4024": "Cambridge O Level Mathematics tutor. Show full step-by-step working.",
    "4037": "Cambridge O Level Additional Mathematics tutor. Show full working.",
    "5054": "Cambridge O Level Physics tutor. Show formulae, substitution and units.",
    "5070": "Cambridge O Level Chemistry tutor. Explain with equations and reasoning.",
    "5090": "Cambridge O Level Biology tutor. Answer in clear mark-scheme points.",
    "2281": "Cambridge O Level Economics tutor. Answer in structured mark-scheme points.",
    "2210": "Cambridge O Level Computer Science tutor. Give precise technical answers.",
    "7707": "Cambridge O Level Accounting tutor. Show ledger/working steps.",
    "9709": "Cambridge A Level Mathematics tutor. Show full step-by-step working.",
    "9702": "Cambridge A Level Physics tutor. Show formulae, substitution and units.",
}


def system_for(subject_code: str) -> str:
    return SUBJECT_PROMPTS.get(subject_code, DEFAULT_SYSTEM_PROMPT)


async def export(subject: str | None, min_chars: int) -> tuple[int, dict]:
    async with models.SessionFactory() as session:
        query = (
            select(AlignedQuestion, PastPaper)
            .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
            .order_by(PastPaper.subject_code, PastPaper.year)
        )
        if subject:
            query = query.where(PastPaper.subject_code == subject)
        rows = (await session.execute(query)).all()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    per_subject: dict[str, int] = {}
    written = 0
    with OUT.open("w", encoding="utf-8") as fh:
        for question, paper in rows:
            q = question.question_markdown.strip()
            a = question.mark_scheme_markdown.strip()
            if len(q) < min_chars or len(a) < min_chars:
                continue
            record = {
                "messages": [
                    {"role": "system", "content": system_for(paper.subject_code)},
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": a},
                ],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            per_subject[paper.subject_code] = per_subject.get(paper.subject_code, 0) + 1
            written += 1
    return written, per_subject


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default=None)
    parser.add_argument("--min-chars", type=int, default=25)
    args = parser.parse_args()

    written, per_subject = asyncio.run(export(args.subject, args.min_chars))
    print(f"Wrote {written} training examples to {OUT}")
    for code in sorted(per_subject):
        print(f"  {code}: {per_subject[code]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
