"""Loads ml-service/.env on import.

Imported first in app.main so LOCAL_LLM and friends are in the
environment before sibling modules (pastpapers.local_llm,
pastpapers.answering, grading, …) read their knobs at import time.
Kept as a module side effect so every import stays at the top of
main.py (ruff E402)."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
