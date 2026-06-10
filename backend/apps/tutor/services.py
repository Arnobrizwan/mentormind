"""AI tutor reply generation.

Provider is environment-selected (dynamic-first):
- GEMINI_API_KEY set       -> Google Gemini (model via GEMINI_MODEL)
- otherwise                -> deterministic stub tutor, so the feature
                              works on a laptop with zero keys and in tests

The free-tier daily message limit is a SiteSetting ('tutor-daily-limit'),
changeable live from the admin console; premium users are unlimited.
"""

import json
import os
import urllib.request

from django.utils import timezone

from apps.settings_engine.services import get_setting

from .models import TutorMessage

DEFAULT_DAILY_LIMIT = 10

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class TutorError(Exception):
    pass


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


def _system_prompt(session):
    subject = session.subject or "general studies"
    level = session.level or "any level"
    return (
        f"You are MentorMind's AI tutor for {subject} at {level}. "
        "Be encouraging and concise. For Math and Physics, always show "
        "step-by-step working. Format answers in Markdown."
    )


def _gemini_reply(session, history):
    api_key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    contents = [
        {
            "role": "model" if m.role == TutorMessage.Role.ASSISTANT else "user",
            "parts": [{"text": m.content}],
        }
        for m in history
    ]
    payload = {
        "system_instruction": {"parts": [{"text": _system_prompt(session)}]},
        "contents": contents,
    }
    request = urllib.request.Request(
        GEMINI_URL.format(model=model) + f"?key={api_key}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as res:
            body = json.load(res)
        return body["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        raise TutorError(f"AI provider error: {exc}") from exc


def _stub_reply(session, history):
    question = history[-1].content if history else ""
    subject = session.subject or "your subject"
    return (
        f"Great question about **{subject}**! Let's work through it step by step.\n\n"
        f"> {question[:200]}\n\n"
        "1. **Identify what's being asked** — restate the problem in your own words.\n"
        "2. **List what you know** — write down the given values or facts.\n"
        "3. **Pick the right tool** — which formula, rule, or concept applies?\n"
        "4. **Work it through** — apply it carefully, one line at a time.\n"
        "5. **Sanity-check** — does the answer's size and unit make sense?\n\n"
        "_(Demo tutor — set GEMINI_API_KEY to get real AI answers.)_"
    )


def generate_reply(session):
    history = list(session.messages.all())
    if os.getenv("GEMINI_API_KEY"):
        return _gemini_reply(session, history)
    return _stub_reply(session, history)
