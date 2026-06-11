from django.db import transaction

from .models import Notification
from .tasks import send_notification_email


def notify(user, kind, title, body="", link=""):
    """Create an in-app notification and queue its email mirror."""
    notification = Notification.objects.create(
        user=user, kind=kind, title=title, body=body, link=link
    )
    # After commit only — otherwise the worker can race the transaction and
    # find no Notification row (or email for one that rolled back).
    transaction.on_commit(lambda: send_notification_email.delay(notification.id))
    return notification
