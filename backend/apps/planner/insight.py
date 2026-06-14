"""One-paragraph "AI insight" for the study planner.

Feeds the student's weakest topics and due-card count into the self-hosted
tutor model (via the ml-service) for a natural coaching tip, and always
falls back to a deterministic, data-driven message so the card renders even
with no model connected — same every-feature-has-a-fallback rule as the tutor.
"""

from django.conf import settings
from django.utils import timezone

from apps.core.adaptive import weak_topics


def _due_count(user) -> int:
    """Flashcards due now. Revision is an optional app, so stay defensive."""
    try:
        from apps.revision.models import ReviewCard

        return ReviewCard.objects.filter(
            user=user, due_at__lte=timezone.now()
        ).count()
    except Exception:  # revision app/table absent at runtime
        return 0


def _fallback_text(topics, due) -> str:
    """Deterministic suggestion — no model required."""
    if topics:
        worst = topics[0]
        names = [t["topic"] for t in topics[:2]]
        topic_str = " and ".join(names) if len(names) > 1 else names[0]
        msg = (
            f"Focus on {topic_str} this week — you're at {worst['accuracy']}% "
            f"on {worst['topic']}, below the 80% comfort line."
        )
        if due:
            cards = "card" if due == 1 else "cards"
            msg += (
                f" Clear your {due} due flash{cards} first to lock in what you "
                f"know, then work through a few {worst['topic']} questions."
            )
        else:
            msg += " Run a short practice set on it, then a timed mock to test yourself."
        return msg
    if due:
        cards = "card is" if due == 1 else "cards are"
        return (
            f"You're solid across your topics — nice work. {due} flash{cards} due "
            "today; a quick review keeps your streak alive and your memory sharp."
        )
    return (
        "You're in great shape — no weak topics flagged and nothing due. Push for "
        "exam readiness with a timed mock exam or start a fresh lesson."
    )


def _llm_text(topics, due) -> str | None:
    """Ask the self-hosted tutor model for a coaching paragraph. Returns None
    when no model is configured, the call fails, or it retrieved a past-paper
    mark scheme (matched) instead of generating advice."""
    if not getattr(settings, "ML_SERVICE_URL", ""):
        return None
    from apps.core import ml_client

    weak_desc = (
        ", ".join(f"{t['topic']} ({t['accuracy']}%)" for t in topics[:3])
        or "none flagged"
    )
    question = (
        "You are a supportive study coach. In one short, encouraging paragraph "
        "(max 60 words), tell the student what to focus on this week and why. "
        f"Their weak topics: {weak_desc}. Flashcards due now: {due}. "
        "Be specific and actionable; do not quote a mark scheme."
    )
    try:
        body = ml_client.post_json(
            "/v1/tutor/answer",
            {"question": question, "subject": "Study planning", "level": "", "history": []},
            timeout=12,
        )
    except Exception:
        return None
    if body.get("matched"):
        return None
    answer = str(body.get("answer", "")).strip()
    return answer or None


def study_insight(user) -> dict:
    try:
        topics = weak_topics(user)[:3]
    except Exception:  # never 500 the card over an analytics query
        topics = []
    due = _due_count(user)
    llm = _llm_text(topics, due)
    return {
        "insight": llm or _fallback_text(topics, due),
        "weak_topics": topics,
        "due_cards": due,
        "source": "model" if llm else "fallback",
    }
