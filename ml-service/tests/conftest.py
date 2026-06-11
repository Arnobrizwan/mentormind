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
def fresh_token_cache():
    """Each test gets a fresh DB, so row ids repeat — drop cached tokens."""
    answering._token_cache.clear()
    yield
