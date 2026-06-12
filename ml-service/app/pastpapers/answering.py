"""Custom tutor answering — grounded in real Cambridge mark schemes.

Strategy, in order:
1. **Retrieval (always on).** Score the student's question against every
   aligned QP question in the corpus (token-overlap cosine). A strong
   match returns the *actual mark scheme working* — a textbook answer,
   not a generated one — with full source attribution.
2. **Fine-tuned model (optional).** When CUSTOM_LLM_URL points at an
   OpenAI-compatible server (vLLM/llama.cpp/Ollama) hosting the model
   you fine-tuned on /api/pipeline/dataset, weak/no matches are answered
   by that model, with the nearest mark schemes injected as grounding
   context. If the server is down, retrieval guidance still answers.

No third-party AI APIs are involved anywhere in this path.
"""

from __future__ import annotations

import asyncio
import math
import os
import re

import httpx
import numpy as np
from sqlalchemy import func, select

from . import local_llm, models
from .models import AlignedQuestion, PastPaper

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "the a an of to in and or for is are be was with on at by it this that "
    "find show state give which what how why your you".split()
)

# Corpus rows scanned per query — plenty for CAIE scale.
MAX_CANDIDATES = int(os.getenv("TUTOR_MAX_CANDIDATES", "5000"))

CUSTOM_LLM_TIMEOUT = float(os.getenv("CUSTOM_LLM_TIMEOUT", "30"))

# Token sets per aligned-question row id, built lazily on first retrieval.
_token_cache: dict[int, set[str]] = {}

_embedding_model = None
_vector_cache: dict[str, np.ndarray] = {}

# Whole-corpus semantic index built from precomputed embeddings
# (scripts/embed_corpus.py). Loaded once per process and rebuilt only when
# the number of embedded rows changes, so query time is one model.encode of
# the question plus a single matrix product over the full corpus.
_index_lock = asyncio.Lock()
_index_ids: list[str] = []
_index_matrix: np.ndarray | None = None
_index_count: int = -1

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Use a fast, small model that runs great on CPU
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Failed to load sentence-transformers: %s", exc)
    return _embedding_model

def get_thresholds():
    model = get_embedding_model()
    is_vector = model is not None
    strong_default = "0.75" if is_vector else "0.45"
    weak_default = "0.50" if is_vector else "0.18"
    return (
        float(os.getenv("TUTOR_STRONG_MATCH", strong_default)),
        float(os.getenv("TUTOR_WEAK_MATCH", weak_default))
    )


def _allowed_llm_url(url: str) -> bool:
    """Only http(s) and never a credentialed URL — a defence-in-depth check
    on the operator-set CUSTOM_LLM_URL so a misconfig can't turn the tutor
    into an SSRF primitive against arbitrary schemes."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.hostname) and "@" not in parsed.netloc


def _tokens(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS}


def _similarity(query: set[str], candidate: set[str]) -> float:
    """Cosine-style overlap on token sets — fast, dependency-free, and
    good enough to find 'the same question, reworded'."""
    if not query or not candidate:
        return 0.0
    overlap = len(query & candidate)
    return overlap / math.sqrt(len(query) * len(candidate))


def _source_of(paper: PastPaper, question: AlignedQuestion) -> dict:
    return {
        "subject_code": paper.subject_code,
        "year": paper.year,
        "session": paper.session,
        "variant": paper.paper_variant,
        "question_number": question.question_number,
    }


async def _load_semantic_index() -> tuple[list[str], np.ndarray | None]:
    """Return (row ids, normalised embedding matrix) for every row that has
    a precomputed embedding. None matrix means the corpus hasn't been run
    through scripts/embed_corpus.py yet — callers fall back to the legacy
    encode-at-request-time path. Rows aligned after the last embed run are
    invisible to the index until the script re-runs."""
    global _index_ids, _index_matrix, _index_count

    async with models.SessionFactory() as session:
        count = (
            await session.execute(
                select(func.count(AlignedQuestion.id)).where(
                    AlignedQuestion.embedding.isnot(None)
                )
            )
        ).scalar_one()
    if count == _index_count:
        return _index_ids, _index_matrix
    if count == 0:
        _index_ids, _index_matrix, _index_count = [], None, 0
        return _index_ids, _index_matrix

    async with _index_lock:
        if count == _index_count:  # another request built it while we waited
            return _index_ids, _index_matrix
        async with models.SessionFactory() as session:
            rows = (
                await session.execute(
                    select(AlignedQuestion.id, AlignedQuestion.embedding).where(
                        AlignedQuestion.embedding.isnot(None)
                    )
                )
            ).all()
        try:
            matrix = np.frombuffer(
                b"".join(blob for _, blob in rows), dtype=np.float32
            ).reshape(len(rows), -1)
        except ValueError:  # mixed dims after a model change — re-run --force
            _index_ids, _index_matrix, _index_count = [], None, 0
            return _index_ids, _index_matrix
        _index_ids = [row_id for row_id, _ in rows]
        _index_matrix = matrix
        _index_count = count
    return _index_ids, _index_matrix


async def _semantic_matches(
    model, question_text: str, limit: int, exclude_ids: set[str] | None
) -> list[tuple[float, AlignedQuestion, PastPaper]] | None:
    """Rank against the precomputed whole-corpus index. None = index not
    available (fall back); a list is a definitive ranking."""
    ids, matrix = await _load_semantic_index()
    if matrix is None or matrix.shape[0] == 0:
        return None
    try:
        q_vec = model.encode(question_text, convert_to_numpy=True).astype(np.float32)
    except Exception:
        return None
    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0 or q_vec.shape[0] != matrix.shape[1]:
        return None
    sims = matrix @ (q_vec / q_norm)

    want = limit + (len(exclude_ids) if exclude_ids else 0)
    if want < len(ids):
        top = np.argpartition(-sims, want - 1)[:want]
        top = top[np.argsort(-sims[top])]
    else:
        top = np.argsort(-sims)
    picked = [
        (ids[i], float(sims[i]))
        for i in top
        if not exclude_ids or ids[i] not in exclude_ids
    ][:limit]
    if not picked:
        return []

    async with models.SessionFactory() as session:
        rows = (
            await session.execute(
                select(AlignedQuestion, PastPaper)
                .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
                .where(AlignedQuestion.id.in_([row_id for row_id, _ in picked]))
            )
        ).all()
    by_id = {aligned.id: (aligned, paper) for aligned, paper in rows}
    return [
        (score, *by_id[row_id]) for row_id, score in picked if row_id in by_id
    ]


async def _ranked_matches(
    question_text: str, limit: int = 3, exclude_ids: set[str] | None = None
) -> list[tuple[float, AlignedQuestion, PastPaper]]:
    model = get_embedding_model()

    if model is not None:
        ranked = await _semantic_matches(model, question_text, limit, exclude_ids)
        if ranked is not None:
            return ranked

    statement = (
        select(AlignedQuestion, PastPaper)
        .join(PastPaper, AlignedQuestion.question_paper_id == PastPaper.id)
        .limit(MAX_CANDIDATES)
    )
    if exclude_ids:
        # Evaluation harness: a question being scored must not retrieve
        # itself, or held-out accuracy is meaninglessly perfect.
        statement = statement.where(AlignedQuestion.id.notin_(exclude_ids))
    async with models.SessionFactory() as session:
        rows = (await session.execute(statement)).all()

    if model is not None:
        if len(_vector_cache) > 2 * MAX_CANDIDATES:
            _vector_cache.clear()
        try:
            q_vec = model.encode(question_text, convert_to_numpy=True)
            q_norm = np.linalg.norm(q_vec)
            if q_norm > 0:
                q_vec = q_vec / q_norm
        except Exception:
            q_vec = None

        if q_vec is not None:
            uncached_indices = []
            uncached_texts = []
            for idx, (aligned, paper) in enumerate(rows):
                if aligned.id not in _vector_cache:
                    uncached_indices.append(idx)
                    uncached_texts.append(aligned.question_markdown)

            if uncached_texts:
                try:
                    embeddings = model.encode(uncached_texts, convert_to_numpy=True)
                    for i, idx in enumerate(uncached_indices):
                        aligned = rows[idx][0]
                        v = embeddings[i]
                        norm = np.linalg.norm(v)
                        _vector_cache[aligned.id] = v / norm if norm > 0 else v
                except Exception:
                    pass

            scored = []
            for aligned, paper in rows:
                v = _vector_cache.get(aligned.id)
                sim = float(np.dot(q_vec, v)) if v is not None else 0.0
                scored.append((sim, aligned, paper))
            scored.sort(key=lambda item: item[0], reverse=True)
            return scored[:limit]

    # Fallback to token-overlap similarity
    query = _tokens(question_text)
    if len(_token_cache) > 2 * MAX_CANDIDATES:
        _token_cache.clear()  # only on a corpus swap; normal growth never trips this
    scored = []
    for aligned, paper in rows:
        candidate = _token_cache.get(aligned.id)
        if candidate is None:
            candidate = _token_cache[aligned.id] = _tokens(aligned.question_markdown)
        scored.append((_similarity(query, candidate), aligned, paper))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:limit]


def _system_prompt(subject: str, level: str, context: str) -> str:
    return (
        f"You are a Cambridge {level or 'O/A Level'} {subject or ''} tutor. "
        "Answer with full step-by-step working in mark-scheme style. "
        "Ground your answer in this reference material:\n\n" + context
    )


async def _generate_answer(
    question: str,
    subject: str,
    level: str,
    context: str,
    history: list[dict] | None = None,
) -> str | None:
    """Generate from the fine-tuned model. Tries fully-offline in-process
    inference first (LOCAL_LLM=1), then an OpenAI-compatible server
    (CUSTOM_LLM_URL). Returns None if neither is available."""
    # In-process inference is CPU/GPU-bound and takes seconds — run it in a
    # worker thread so it can't stall the event loop.
    local = await asyncio.to_thread(
        local_llm.generate,
        question,
        _system_prompt(subject, level, ""),
        context,
        history,
    )
    if local:
        return local

    url = os.getenv("CUSTOM_LLM_URL", "")
    if not url or not _allowed_llm_url(url):
        return None

    messages = [
        {"role": "system", "content": _system_prompt(subject, level, context)},
    ]
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    payload = {
        "model": os.getenv("CUSTOM_LLM_MODEL", "mentormind-tutor"),
        "messages": messages,
        "temperature": 0.2,
    }
    try:
        # async client — a slow LLM server must not block the event loop
        async with httpx.AsyncClient(timeout=CUSTOM_LLM_TIMEOUT) as client:
            response = await client.post(
                url.rstrip("/") + "/v1/chat/completions", json=payload
            )
            response.raise_for_status()
            body = response.json()
        return body["choices"][0]["message"]["content"]
    except Exception:
        return None


async def answer_question(
    question: str,
    subject: str = "",
    level: str = "",
    exclude_ids: set[str] | None = None,
    history: list[dict] | None = None,
) -> dict:
    """Answer a student's question from the past-paper corpus.

    Returns {"answer": str, "matched": bool, "source": dict | None}.
    exclude_ids is for the evaluation harness only (leave-one-out).
    """
    strong_match, weak_match = get_thresholds()
    matches = await _ranked_matches(question, exclude_ids=exclude_ids)
    best = matches[0] if matches else None

    # 1) Strong match — return the real mark-scheme working verbatim.
    if best and best[0] >= strong_match:
        score, aligned, paper = best
        answer = (
            "Here is the official mark-scheme working for this question:\n\n"
            f"**Question** (as set):\n\n{aligned.question_markdown}\n\n"
            f"**Step-by-step solution:**\n\n{aligned.mark_scheme_markdown}"
        )
        return {"answer": answer, "matched": True, "source": _source_of(paper, aligned)}

    # 2) Weak/no match — try the fine-tuned model with retrieved grounding.
    context = "\n\n---\n\n".join(
        f"Q: {aligned.question_markdown}\nMark scheme: {aligned.mark_scheme_markdown}"
        for score, aligned, paper in matches
        if score >= weak_match
    )
    generated = await _generate_answer(question, subject, level, context, history)
    if generated:
        source = _source_of(matches[0][2], matches[0][1]) if context else None
        return {"answer": generated, "matched": False, "source": source}

    # 3) Retrieval guidance from the nearest mark scheme.
    if best and best[0] >= weak_match:
        score, aligned, paper = best
        answer = (
            "I couldn't find this exact question in the corpus, but here is "
            "the closest past-paper question and its mark scheme — the same "
            "method applies:\n\n"
            f"**Similar question:**\n\n{aligned.question_markdown}\n\n"
            f"**Mark-scheme method:**\n\n{aligned.mark_scheme_markdown}"
        )
        return {"answer": answer, "matched": False, "source": _source_of(paper, aligned)}

    # 4) Nothing useful in the corpus yet.
    return {
        "answer": (
            "This question isn't covered by the aligned past-paper corpus yet. "
            "Run more papers through the pipeline (POST /api/pipeline/process-next) "
            "to expand coverage, then ask again."
        ),
        "matched": False,
        "source": None,
    }
