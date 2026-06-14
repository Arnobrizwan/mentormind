"""AI tutor reply generation — fully custom, no third-party AI providers.

Provider chain (environment-selected, dynamic-first):
- TUTOR_MODEL_URL set -> POST to your own model server. In this stack
  that is the ml-service answer endpoint, which grounds every reply in
  real Cambridge mark schemes built by the past-paper pipeline (and can
  front a fine-tuned model trained on /api/pipeline/dataset).
- otherwise            -> deterministic stub, so the feature works on a
  laptop with zero services and in tests.

The free-tier daily message limit is a SiteSetting ('tutor-daily-limit'),
changeable live from the admin console; premium users are unlimited.
"""

import json
import os
import urllib.request

from django.conf import settings
from django.utils import timezone

from apps.settings_engine.services import get_setting

from .models import TutorMessage

DEFAULT_DAILY_LIMIT = 10
# Keep this short — the request handler blocks for the full duration when
# the model server hangs.
MODEL_TIMEOUT_SECONDS = int(os.getenv("TUTOR_MODEL_TIMEOUT_SECONDS", "15"))
HISTORY_WINDOW = 10


class TutorError(Exception):
    pass


# Mirrors the ml-service's own MAX_IMAGE_BYTES cap.
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def describe_image(uploaded_file, question=""):
    """Understand a photographed question through the ml-service, so a student
    can snap a textbook problem (or a diagram) instead of typing it.

    Routes to /v1/vision/ask, which uses the moondream2 VLM to actually 'see'
    figures and handwriting when VISION_VLM=1, and transparently degrades to
    OCR text otherwise — so the Snap-&-Solve flow always returns something.
    The student's typed text is forwarded as the question to focus the model.

    Returns the description/answer (possibly empty); raises TutorError on bad
    input or a dead ml-service."""
    from apps.core import ml_client

    if not (uploaded_file.content_type or "").startswith("image/"):
        raise TutorError("Only image uploads are supported.")
    raw = uploaded_file.read()
    if len(raw) > MAX_IMAGE_BYTES:
        raise TutorError("Image too large (8 MB max).")
    try:
        body = ml_client.post_image(
            "/v1/vision/ask",
            raw,
            filename=uploaded_file.name or "question.jpg",
            content_type=uploaded_file.content_type,
            fields={"question": (question or "").strip()},
        )
    except ml_client.MLServiceError as exc:
        raise TutorError(f"Could not read the photo: {exc}") from exc
    # /v1/vision/ask returns {"answer": ...}; OCR-only deployments may still
    # return {"text": ...}, so accept either.
    return str(body.get("answer") or body.get("text") or "").strip()


def daily_limit(user):
    """None means unlimited (premium)."""
    if getattr(user, "is_premium", False):
        return None
    configured = get_setting("tutor-daily-limit")
    return configured if isinstance(configured, int) else DEFAULT_DAILY_LIMIT


def messages_used_today(user):
    return TutorMessage.objects.filter(
        session__user=user,
        role=TutorMessage.Role.USER,
        created_at__date=timezone.localdate(),
    ).count()


def remaining_today(user):
    limit = daily_limit(user)
    if limit is None:
        return None
    return max(0, limit - messages_used_today(user))


def _post_json(url, payload, timeout=MODEL_TIMEOUT_SECONDS):
    """Tiny JSON-over-HTTP client — kept separate so tests can stub it."""
    headers = {"Content-Type": "application/json"}
    # The ml-service requires its shared X-API-Key when ML_API_KEY is set
    if getattr(settings, "ML_API_KEY", ""):
        headers["X-API-Key"] = settings.ML_API_KEY
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _custom_model_reply(session, history):
    """Ask the self-hosted model server (ml-service or any compatible
    endpoint serving the fine-tuned past-paper model).

    Contract:  POST {question, subject, level, history[]}
            -> {answer: str, matched: bool, source: {...}|null}
    """
    url = os.environ["TUTOR_MODEL_URL"]
    payload = {
        "question": history[-1].content if history else "",
        "subject": session.subject,
        "level": session.level,
        "history": [
            {"role": m.role, "content": m.content}
            for m in history[:-1][-HISTORY_WINDOW:]
        ],
    }
    try:
        body = _post_json(url, payload)
    except Exception as exc:
        raise TutorError(f"Custom model server unreachable: {exc}") from exc

    answer = str(body.get("answer", "")).strip()
    if not answer:
        raise TutorError("Custom model server returned an empty answer.")

    source = body.get("source")
    if body.get("matched") and isinstance(source, dict):
        answer += (
            "\n\n---\n*Source: Cambridge {subject} {session}{year} "
            "Paper {variant} Q{number} mark scheme.*".format(
                subject=source.get("subject_code", "?"),
                session=source.get("session", "?"),
                year=source.get("year", "?"),
                variant=source.get("variant", "?"),
                number=source.get("question_number", "?"),
            )
        )
    return answer


def _stub_reply(session, history):
    # No model is connected, so never pretend to know the subject matter —
    # offer the universal problem-solving scaffold and say what this is.
    question = history[-1].content if history else ""
    return (
        "I can't give a full worked answer right now (no tutor model is "
        "connected), but here's how to attack it step by step:\n\n"
        f"> {question[:200]}\n\n"
        "1. **Identify what's being asked** — restate the problem in your own words.\n"
        "2. **List what you know** — write down the given values or facts.\n"
        "3. **Pick the right tool** — which formula, rule, or concept applies?\n"
        "4. **Work it through** — apply it carefully, one line at a time.\n"
        "5. **Sanity-check** — does the answer's size and unit make sense?\n\n"
        "_(Demo tutor — point TUTOR_MODEL_URL at your model server for real "
        "mark-scheme-grounded answers.)_"
    )


def generate_reply(session):
    # Query explicitly — the viewset prefetches `messages`, and that cache
    # predates the user message we just persisted.
    history = list(
        TutorMessage.objects.filter(session=session).order_by("created_at")
    )
    if os.getenv("TUTOR_MODEL_URL"):
        return _custom_model_reply(session, history)
    return _stub_reply(session, history)
