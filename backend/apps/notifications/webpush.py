"""Web Push delivery — VAPID-signed, self-hosted, no third-party service.

The whole module is a no-op unless VAPID keys are configured (settings
VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY), so the feature ships OFF by default and
the rest of the app — and the test suite — runs without the optional
`pywebpush` dependency installed.
"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def is_configured():
    """True when push can actually be sent (keys present + lib importable)."""
    if not (settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY):
        return False
    try:
        import pywebpush  # noqa: F401
    except ImportError:
        logger.warning("VAPID keys set but pywebpush is not installed.")
        return False
    return True


def public_key():
    return settings.VAPID_PUBLIC_KEY


def send_to_user(user, *, title, body, url="/", tag="mentormind"):
    """Push a notification to every live subscription a user has.

    Returns the number of successful sends. Subscriptions the push service
    rejects as gone (404/410) are deleted so the table self-heals.
    """
    if not is_configured():
        return 0

    from pywebpush import WebPushException, webpush

    from .models import PushSubscription

    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    vapid_claims = {"sub": settings.VAPID_SUBJECT}
    sent = 0
    dead_ids = []

    for sub in PushSubscription.objects.filter(user=user):
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=dict(vapid_claims),
                timeout=10,
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                dead_ids.append(sub.id)  # subscription expired/unsubscribed
            else:
                logger.warning("Web push failed for %s: %s", sub.endpoint[-12:], exc)
        except Exception as exc:  # never let a bad endpoint break a batch
            logger.warning("Web push error: %s", exc)

    if dead_ids:
        PushSubscription.objects.filter(id__in=dead_ids).delete()
    return sent
