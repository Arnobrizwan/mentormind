"""Precompute sentence embeddings for the aligned past-paper corpus.

Encodes every aligned question's text with the same MiniLM model the
tutor uses at query time and persists the L2-normalised float32 vector
on the row. After this runs, retrieval never has to encode the corpus
in-process — only the incoming query — so cold starts drop from minutes
to seconds and the semantic index covers the whole corpus.

Idempotent: only rows with a NULL embedding are encoded. Re-run after
the pipeline aligns new papers, or use --force after changing the model.

    .venv/bin/python scripts/embed_corpus.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import numpy as np
from sqlalchemy import func, select, update

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import env as _env  # load .env exactly like the served app
from app.pastpapers import answering
from app.pastpapers.models import AlignedQuestion, SessionFactory, init_db

BATCH = 512  # rows encoded + committed per round trip


async def run(force: bool) -> int:
    await init_db()
    model = answering.get_embedding_model()
    if model is None:
        print("sentence-transformers unavailable — nothing to precompute.")
        return 1

    async with SessionFactory() as session:
        total = (await session.execute(select(func.count(AlignedQuestion.id)))).scalar_one()
        if force:
            await session.execute(update(AlignedQuestion).values(embedding=None))
            await session.commit()

    done = 0
    started = time.monotonic()
    while True:
        async with SessionFactory() as session:
            rows = (
                await session.execute(
                    select(AlignedQuestion.id, AlignedQuestion.question_markdown)
                    .where(AlignedQuestion.embedding.is_(None))
                    .limit(BATCH)
                )
            ).all()
            if not rows:
                break

            vectors = model.encode(
                [text for _, text in rows], convert_to_numpy=True, batch_size=64
            ).astype(np.float32)
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vectors /= norms

            for (row_id, _), vector in zip(rows, vectors):
                await session.execute(
                    update(AlignedQuestion)
                    .where(AlignedQuestion.id == row_id)
                    .values(embedding=vector.tobytes())
                )
            await session.commit()

        done += len(rows)
        rate = done / max(time.monotonic() - started, 1e-9)
        print(f"embedded {done} rows ({rate:.0f}/s, corpus {total})", flush=True)

    print(f"done — {done} rows embedded this run, corpus size {total}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="re-embed every row (model change)"
    )
    args = parser.parse_args()
    return asyncio.run(run(args.force))


if __name__ == "__main__":
    raise SystemExit(main())
