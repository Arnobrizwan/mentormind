from .models import Notification
from .tasks import send_notification_email


def notify(user, kind, title, body="", link=""):
    """Create an in-app notification and queue its email mirror."""
    notification = Notification.objects.create(
        user=user, kind=kind, title=title, body=body, link=link
    )
    send_notification_email.delay(notification.id)
    return notification
