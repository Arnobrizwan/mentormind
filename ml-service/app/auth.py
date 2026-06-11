"""Service-wide API-key auth for inference and pipeline endpoints.

Callers present X-API-Key matching env ML_API_KEY. A missing key config is
a hard 503 (fail closed) unless ML_ALLOW_UNAUTHENTICATED=1 — an explicit
local-dev opt-in, never the silent default.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Global key for every inference/pipeline route. Health, model listing
    and /metrics stay open for orchestrators and Prometheus scrapes."""
    key = os.getenv("ML_API_KEY", "")
    if not key:
        if os.getenv("ML_ALLOW_UNAUTHENTICATED") == "1":
            return
        raise HTTPException(status_code=503, detail="ML_API_KEY not configured")
    if not hmac.compare_digest(x_api_key, key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
