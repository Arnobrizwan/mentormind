"""Tutor harness evaluation gate — Self-Harness style (arXiv:2606.09498).

Scores the *whole answering harness* (retrieval thresholds, prompts,
local-LLM chain, fallbacks) against the aligned past-paper corpus, where
the official mark scheme is ground truth. Questions are split
deterministically into HELD-IN and HELD-OUT; each is answered
leave-one-out (the question can't retrieve itself), and the answer is
scored by mark-scheme token recall.

Use it as the paper's validation gate: run before and after any prompt,
threshold, or model change —

    .venv/bin/python scripts/eval_tutor.py --max 40

— and accept the change only if held-in improves WITHOUT held-out
degrading. The fallback-path breakdown doubles as weakness mining:
a rising 'unanswered' or 'guidance' share tells you where the harness
fails before students do.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import env as _env  # load .env exactly like the served app
from app.pastpapers import answering
from app.pastpapers.answering import _tokens
from app.pastpapers.models import AlignedQuestion, SessionFactory, init_db

HOLDOUT_BUCKETS = 5  # id-hash % 5 == 0 -> held-out (~20%)


def split_of(question_id: str) -> str:
    digest = hashlib.sha256(question_id.encode()).digest()
    return "held-out" if digest[0] % HOLDOUT_BUCKETS == 0 else "held-in"


def recall(answer: str, mark_scheme: str) -> float:
    """Fraction of the mark scheme's content tokens present in the answer."""
    scheme_tokens = _tokens(mark_scheme)
    if not scheme_tokens:
        return 0.0
    return len(_tokens(answer) & scheme_tokens) / len(scheme_tokens)


def path_of(result: dict) -> str:
    if result["matched"]:
        return "retrieval"
    answer = result["answer"]
    if answer.startswith("I couldn't find this exact question"):
        return "guidance"
    if answer.startswith("This question isn't covered"):
        return "unanswered"
    return "llm"


async def run(max_per_split: int, splits: list[str]) -> int:
    await init_db()
    async with SessionFactory() as session:
        from sqlalchemy import select

        rows = (await session.execute(select(AlignedQuestion))).scalars().all()
    if not rows:
        print("Corpus is empty — run the pipeline first (POST /api/pipeline/process-next).")
        return 1

    buckets: dict[str, list[AlignedQuestion]] = {name: [] for name in splits}
    for row in sorted(rows, key=lambda r: r.id):
        bucket = split_of(row.id)
        if bucket in buckets and len(buckets[bucket]) < max_per_split:
            buckets[bucket].append(row)

    print(f"corpus: {len(rows)} aligned questions | evaluating "
          + ", ".join(f"{name}: {len(qs)}" for name, qs in buckets.items()))

    overall_rc = 0
    for name, questions in buckets.items():
        scores: list[float] = []
        paths: dict[str, int] = {}
        started = time.monotonic()
        for question in questions:
            result = await answering.answer_question(
                question.question_markdown, exclude_ids={question.id}
            )
            scores.append(recall(result["answer"], question.mark_scheme_markdown))
            paths[path_of(result)] = paths.get(path_of(result), 0) + 1
        elapsed = time.monotonic() - started

        if not scores:
            print(f"\n[{name}] no questions in split")
            continue
        mean = sum(scores) / len(scores)
        strong = sum(1 for s in scores if s >= 0.5)
        print(f"\n[{name}] n={len(scores)}  mean mark-scheme recall={mean:.3f}  "
              f">=0.5 recall: {strong}/{len(scores)}  ({elapsed:.0f}s)")
        print("  answer paths: " + ", ".join(f"{k}={v}" for k, v in sorted(paths.items())))

    print(
        "\nGate: accept a harness change only if held-in improves and "
        "held-out does not degrade (re-run with identical --max)."
    )
    return overall_rc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max", type=int, default=30, help="questions per split")
    parser.add_argument(
        "--split",
        choices=["held-in", "held-out", "both"],
        default="both",
    )
    args = parser.parse_args()
    splits = ["held-in", "held-out"] if args.split == "both" else [args.split]
    return asyncio.run(run(args.max, splits))


if __name__ == "__main__":
    raise SystemExit(main())
