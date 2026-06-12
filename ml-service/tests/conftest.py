"""Shared test setup — auth opt-in and per-test cache isolation."""

import pytest

from app.pastpapers import answering


@pytest.fixture(autouse=True)
def open_auth(monkeypatch):
    """Endpoint tests exercise inference logic, not auth — use the explicit
    local-dev opt-in. test_auth.py overrides these to cover the key paths."""
    monkeypatch.delenv("ML_API_KEY", raising=False)
    monkeypatch.setenv("ML_ALLOW_UNAUTHENTICATED", "1")


@pytest.fixture(autouse=True)
def no_local_llm(monkeypatch):
    """Tests must be hermetic: a developer's .env (loaded by app.main) may
    set LOCAL_LLM=1, which would run real model inference inside the suite
    and change retrieval-fallback answers. Tests that cover the local path
    set LOCAL_LLM explicitly."""
    monkeypatch.delenv("LOCAL_LLM", raising=False)


@pytest.fixture(autouse=True)
def fresh_token_cache():
    """Each test gets a fresh DB, so row ids repeat — drop cached tokens,
    cached vectors, and the precomputed semantic index."""
    answering._token_cache.clear()
    answering._vector_cache.clear()
    answering._index_ids = []
    answering._index_matrix = None
    answering._index_count = -1
    yield
