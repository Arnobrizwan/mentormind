from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_notification_email(notification_id):
    """Mirror an in-app notification to email. Runs on the Celery worker
    (eager fallback without Redis, console email backend in dev)."""
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
        fail_silently=True,
    )
    return f"emailed {notification.user.email}"
