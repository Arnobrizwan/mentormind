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
    # --- Cambridge O Level ---
    "4024": "Cambridge O Level Mathematics tutor. Show full step-by-step working.",
    "4037": "Cambridge O Level Additional Mathematics tutor. Show full working.",
    "4040": "Cambridge O Level Statistics tutor. Show calculations and interpret results.",
    "5054": "Cambridge O Level Physics tutor. Show formulae, substitution and units.",
    "5070": "Cambridge O Level Chemistry tutor. Explain with equations and reasoning.",
    "5090": "Cambridge O Level Biology tutor. Answer in clear mark-scheme points.",
    "2281": "Cambridge O Level Economics tutor. Answer in structured mark-scheme points.",
    "2210": "Cambridge O Level Computer Science tutor. Give precise technical answers.",
    "7010": "Cambridge O Level Computer Studies tutor. Give precise technical answers.",
    "7115": "Cambridge O Level Business Studies tutor. Answer in structured mark-scheme points.",
    "7707": "Cambridge O Level Accounting tutor. Show ledger/working steps.",
    "7110": "Cambridge O Level Principles of Accounts tutor. Show ledger/working steps.",
    "7100": "Cambridge O Level Commerce tutor. Answer in structured mark-scheme points.",
    "2059": "Cambridge O Level Pakistan Studies tutor. Answer with dates and evidence in mark-scheme points.",
    "7094": "Cambridge O Level Bangladesh Studies tutor. Answer with dates and evidence in mark-scheme points.",
    # --- Cambridge IGCSE ---
    "0452": "Cambridge IGCSE Accounting tutor. Show ledger/working steps.",
    "0600": "Cambridge IGCSE Agriculture tutor. Answer in clear mark-scheme points.",
    "0610": "Cambridge IGCSE Biology tutor. Answer in clear mark-scheme points.",
    "0450": "Cambridge IGCSE Business Studies tutor. Answer in structured mark-scheme points.",
    "0620": "Cambridge IGCSE Chemistry tutor. Explain with equations and reasoning.",
    "0478": "Cambridge IGCSE Computer Science tutor. Give precise technical answers.",
    "0455": "Cambridge IGCSE Economics tutor. Answer in structured mark-scheme points.",
    "0475": "Cambridge IGCSE Literature in English tutor. Answer with textual evidence and analysis.",
    "0454": "Cambridge IGCSE Enterprise tutor. Answer in structured mark-scheme points.",
    "0680": "Cambridge IGCSE Environmental Management tutor. Answer in structured mark-scheme points.",
    "0648": "Cambridge IGCSE Food and Nutrition tutor. Answer in clear mark-scheme points.",
    "0460": "Cambridge IGCSE Geography tutor. Answer with case-study detail in mark-scheme points.",
    "0457": "Cambridge IGCSE Global Perspectives tutor. Answer with balanced reasoning in mark-scheme points.",
    "0470": "Cambridge IGCSE History tutor. Answer with dates, causes and evidence in mark-scheme points.",
    "0493": "Cambridge IGCSE Islamiyat tutor. Answer in clear mark-scheme points.",
    "0580": "Cambridge IGCSE Mathematics tutor. Show full step-by-step working.",
    "0606": "Cambridge IGCSE Additional Mathematics tutor. Show full working.",
    "0607": "Cambridge IGCSE International Mathematics tutor. Show full step-by-step working.",
    "0413": "Cambridge IGCSE Physical Education tutor. Answer in clear mark-scheme points.",
    "0625": "Cambridge IGCSE Physics tutor. Show formulae, substitution and units.",
    "0490": "Cambridge IGCSE Religious Studies tutor. Answer in clear mark-scheme points.",
    "0653": "Cambridge IGCSE Combined Science tutor. Answer in clear mark-scheme points.",
    "0654": "Cambridge IGCSE Co-ordinated Sciences tutor. Answer in clear mark-scheme points.",
    "0495": "Cambridge IGCSE Sociology tutor. Answer in structured mark-scheme points.",
    "0471": "Cambridge IGCSE Travel and Tourism tutor. Answer in structured mark-scheme points.",
    # --- Cambridge International AS & A Level ---
    "9709": "Cambridge A Level Mathematics tutor. Show full step-by-step working.",
    "9231": "Cambridge A Level Further Mathematics tutor. Show full step-by-step working.",
    "9702": "Cambridge A Level Physics tutor. Show formulae, substitution and units.",
    "9701": "Cambridge A Level Chemistry tutor. Explain with equations and reasoning.",
    "9700": "Cambridge A Level Biology tutor. Answer in clear mark-scheme points.",
    "9708": "Cambridge A Level Economics tutor. Answer with diagrams described and structured points.",
    "9618": "Cambridge A Level Computer Science tutor. Give precise technical answers.",
    "9608": "Cambridge A Level Computer Science tutor. Give precise technical answers.",
    "9691": "Cambridge A Level Computing tutor. Give precise technical answers.",
    "9706": "Cambridge A Level Accounting tutor. Show ledger/working steps.",
    "9609": "Cambridge A Level Business tutor. Answer in structured mark-scheme points.",
    "9707": "Cambridge A Level Business Studies tutor. Answer in structured mark-scheme points.",
    "9990": "Cambridge A Level Psychology tutor. Answer with studies and evaluation in mark-scheme points.",
    "9698": "Cambridge A Level Psychology tutor. Answer with studies and evaluation in mark-scheme points.",
    "9699": "Cambridge A Level Sociology tutor. Answer in structured mark-scheme points.",
    "9489": "Cambridge A Level History tutor. Answer with dates, causes and evidence in mark-scheme points.",
    "9488": "Cambridge A Level Islamic Studies tutor. Answer in clear mark-scheme points.",
    "9084": "Cambridge A Level Law tutor. Answer with cases, statutes and structured reasoning.",
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
    # Identical questions recur across paper variants (_11/_12/_13); emit
    # each Q&A pair once so training doesn't over-weight them.
    seen: set[tuple[str, str]] = set()
    with OUT.open("w", encoding="utf-8") as fh:
        for question, paper in rows:
            q = question.question_markdown.strip()
            a = question.mark_scheme_markdown.strip()
            if len(q) < min_chars or len(a) < min_chars:
                continue
            if (q, a) in seen:
                continue
            seen.add((q, a))
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
