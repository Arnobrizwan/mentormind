from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_revision_reminders():
    """Daily web-push nudge: students with due flashcards (or a streak worth
    protecting) get a reminder. No-op when push isn't configured."""
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from apps.engagement.models import DailyActivity
    from apps.engagement.services import current_streak
    from apps.revision.models import ReviewCard

    from . import webpush

    if not webpush.is_configured():
        return "push not configured"

    User = get_user_model()
    now = timezone.now()
    today = timezone.localdate()
    sent = 0
    # Only users who actually opted in have subscriptions — iterate those.
    # Force the primary DB so freshly-scheduled cards and today's activity are
    # reflected (the read-replica router would otherwise serve stale counts).
    user_ids = (
        User.objects.using("default")
        .filter(push_subscriptions__isnull=False)
        .distinct()
        .values_list("id", flat=True)
    )
    for user in User.objects.using("default").filter(id__in=list(user_ids)):
        due = (
            ReviewCard.objects.using("default")
            .filter(user=user, due_at__lte=now, flashcard__is_published=True)
            .count()
        )
        if due:
            title = "📚 Time to revise"
            body = f"You have {due} flashcard{'s' if due != 1 else ''} due today."
        else:
            # Only nudge about the streak if they haven't already studied
            # today — otherwise an engaged daily user gets pinged every evening.
            studied_today = (
                DailyActivity.objects.using("default")
                .filter(user=user, date=today)
                .exists()
            )
            streak = current_streak(user)
            if studied_today or not streak:
                continue
            title = f"🔥 Keep your {streak}-day streak"
            body = "A few minutes of study keeps your streak alive."
        sent += webpush.send_to_user(user, title=title, body=body, url="/revision")
    return f"sent {sent} reminder push(es)"


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_notification_email(notification_id):
    """Mirror an in-app notification to email. Runs on the Celery worker
    (eager fallback without Redis, console email backend in dev).
    SMTP hiccups raise and retry with backoff; Celery logs the final failure."""
    from .models import Notification

    from apps.settings_engine.services import get_setting

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return "notification gone"

    brand = get_setting("site-name") or "MentorMind"
    send_mail(
        subject=f"[{brand}] {notification.title}",
        message=notification.body or notification.title,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[notification.user.email],
        fail_silently=False,
    )
    return f"emailed {notification.user.email}"
