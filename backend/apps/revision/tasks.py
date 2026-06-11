import logging

from celery import shared_task

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 16000
CARDS_PER_LESSON = 10


@shared_task
def generate_flashcards_for_lesson(lesson_id, requested_by_id):
    """Ask the ml-service to draft flashcards from a lesson's content and
    file them as unpublished drafts for instructor review."""
    from apps.core import ml_client
    from apps.core.models import Lesson
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    from .models import Flashcard

    try:
        lesson = Lesson.objects.select_related("course").get(id=lesson_id)
    except Lesson.DoesNotExist:
        return "lesson gone"

    try:
        body = ml_client.post_json(
            "/v1/generate/flashcards",
            {
                "content": lesson.content[:MAX_CONTENT_CHARS],
                "topic": lesson.title,
                "count": CARDS_PER_LESSON,
            },
            timeout=120,  # may run the in-process LLM
        )
    except ml_client.MLServiceError as exc:
        logger.warning("flashcard generation failed for lesson %s: %s", lesson_id, exc)
        return f"ml-service error: {exc}"

    engine = body.get("engine")
    source = Flashcard.Source.LLM if engine == "llm" else Flashcard.Source.HEURISTIC
    created = 0
    for card in body.get("cards") or []:
        front = str(card.get("front", "")).strip()
        back = str(card.get("back", "")).strip()
        if not front or not back:
            continue
        Flashcard.objects.create(
            course=lesson.course,
            lesson=lesson,
            topic=lesson.title[:100],
            front=front,
            back=back,
            source=source,
            is_published=False,
        )
        created += 1

    from django.contrib.auth import get_user_model

    try:
        instructor = get_user_model().objects.get(id=requested_by_id)
    except get_user_model().DoesNotExist:
        instructor = None
    if instructor and created:
        notify(
            instructor,
            Notification.Kind.SYSTEM,
            title=f"{created} flashcard drafts ready for review",
            body=f"AI-generated cards for '{lesson.title}' are waiting for your "
            "approval before students see them.",
            link=f"/courses/{lesson.course.slug}",
        )
    return f"created {created} draft card(s)"
