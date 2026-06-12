from celery import shared_task


@shared_task
def check_badges_for_user(user_id, action=""):
    """Badge evaluation off the request path — every points event used to
    aggregate all eight rules synchronously."""
    from django.contrib.auth import get_user_model

    from .services import check_badges

    try:
        user = get_user_model().objects.get(id=user_id)
    except get_user_model().DoesNotExist:
        return "user gone"
    fresh = check_badges(user, action=action)
    return f"awarded {len(fresh)} badge(s)"


@shared_task
def scan_dropout_risk():
    """Weekly student-success sweep (Celery beat): score every active
    enrolled student against the ml-service dropout model; nudge and
    ticket the high-risk ones. Also runnable on demand from the
    instructor studio."""
    from django.core.cache import cache

    from .risk import scan_students

    try:
        scanned, flagged = scan_students()
    finally:
        # Free the on-demand trigger's single-flight lock as soon as the
        # sweep ends (the lock also self-expires after 10 minutes).
        cache.delete("engagement:dropout-scan-lock")
    return f"scanned {scanned} student(s), flagged {flagged} high-risk"


@shared_task
def send_weekly_digest():
    """Sunday-evening summary (Celery beat): points earned this week,
    streak, due flashcards, and the weakest topic — skipping students with
    nothing to say."""
    from datetime import timedelta

    from django.contrib.auth import get_user_model
    from django.db.models import Sum
    from django.utils import timezone

    from apps.core.adaptive import weak_topics
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    from .models import PointsEvent
    from .services import current_streak

    User = get_user_model()
    since = timezone.now() - timedelta(days=7)
    sent = 0
    students = (
        User.objects.filter(is_active=True, enrollments__isnull=False)
        .distinct()
        .order_by("id")
    )
    for user in students.iterator():
        points = (
            PointsEvent.objects.using("default")
            .filter(user=user, created_at__gte=since)
            .aggregate(total=Sum("points"))["total"]
            or 0
        )
        due = 0
        try:
            from apps.revision.models import ReviewCard

            due = ReviewCard.objects.using("default").filter(
                user=user,
                due_at__lte=timezone.now(),
                flashcard__is_published=True,
            ).count()
        except Exception:
            pass
        if points == 0 and due == 0:
            continue
        weakest = weak_topics(user)[:1]
        lines = [f"You earned {points} points this week."]
        streak = current_streak(user)
        if streak:
            lines.append(f"Your streak is {streak} day(s) — keep it alive!")
        if due:
            lines.append(f"{due} flashcard(s) are due for revision.")
        if weakest:
            lines.append(
                f"Focus suggestion: {weakest[0]['topic']} "
                f"({weakest[0]['accuracy']}% accuracy)."
            )
        notify(
            user,
            Notification.Kind.SYSTEM,
            title="Your week at MentorMind 📬",
            body=" ".join(lines),
            link="/dashboard",
        )
        sent += 1
    return f"digest sent to {sent} student(s)"
