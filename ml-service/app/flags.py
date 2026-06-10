"""Feature-flag awareness for the ML service.

The flags live in the main API's database and toggle live from the admin
console. This service polls the public /api/v1/flags/ endpoint (set
FLAGS_URL, e.g. http://nginx/api/v1/flags/) with a short cache.

Fail-open by design: if FLAGS_URL is unset, the API is unreachable, or a
flag simply doesn't exist, the feature stays enabled — flags here are a
kill switch, not an allow-list.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request

FLAGS_URL = os.getenv("FLAGS_URL", "")
FLAGS_TTL_SECONDS = float(os.getenv("FLAGS_TTL_SECONDS", "30"))

_cache: dict = {"at": 0.0, "flags": {}}


def flag_enabled(key: str, default: bool = True) -> bool:
    if not FLAGS_URL:
        return default

    now = time.monotonic()
    if now - _cache["at"] > FLAGS_TTL_SECONDS:
        try:
            with urllib.request.urlopen(FLAGS_URL, timeout=2) as res:
                _cache["flags"] = json.load(res)
        except Exception:
            pass  # keep the last known flags; fail open on first failure
        _cache["at"] = now

    return bool(_cache["flags"].get(key, default))
