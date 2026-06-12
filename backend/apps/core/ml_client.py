"""Stdlib client for the FastAPI ml-service.

One place owns the base URL, the X-API-Key header, and error wrapping, so
feature code (tutor OCR, proctoring, grading, dropout risk) never builds
requests by hand. Deliberately urllib-only — the backend carries no HTTP
client dependency.
"""

import json
import secrets
import urllib.request

from django.conf import settings

DEFAULT_TIMEOUT_SECONDS = 15


class MLServiceError(Exception):
    """The ml-service is unreachable, misconfigured, or returned junk."""


def _base_url():
    url = getattr(settings, "ML_SERVICE_URL", "")
    if not url:
        raise MLServiceError("ML_SERVICE_URL is not configured.")
    return url.rstrip("/")


def _auth_headers():
    if getattr(settings, "ML_API_KEY", ""):
        return {"X-API-Key": settings.ML_API_KEY}
    return {}


def _send(request, path, timeout):
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except MLServiceError:
        raise
    except Exception as exc:
        raise MLServiceError(f"ml-service {path} failed: {exc}") from exc


def post_json(path, payload, timeout=DEFAULT_TIMEOUT_SECONDS):
    """POST a JSON body to the ml-service, return the decoded JSON reply."""
    request = urllib.request.Request(
        _base_url() + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **_auth_headers()},
        method="POST",
    )
    return _send(request, path, timeout)


def get_json(path, timeout=DEFAULT_TIMEOUT_SECONDS):
    """GET a JSON document from the ml-service."""
    request = urllib.request.Request(
        _base_url() + path, headers=_auth_headers(), method="GET"
    )
    return _send(request, path, timeout)


def post_image(
    path,
    image_bytes,
    filename="upload.jpg",
    content_type="image/jpeg",
    fields=None,
    timeout=DEFAULT_TIMEOUT_SECONDS,
):
    """POST an image (plus optional extra form fields) as multipart/form-data.
    The ml-service vision endpoints all take the file under the name 'image'."""
    boundary = "----mentormind-" + secrets.token_hex(16)
    parts = []
    for name, value in (fields or {}).items():
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
                f"\r\n\r\n{value}\r\n"
            ).encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
            f'filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'
        ).encode()
        + image_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    request = urllib.request.Request(
        _base_url() + path,
        data=b"".join(parts),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            **_auth_headers(),
        },
        method="POST",
    )
    return _send(request, path, timeout)
