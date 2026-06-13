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


# Cap the fan-out so a user with many devices (or a batch job calling this per
# user) can't spawn an unbounded number of threads.
_MAX_PUSH_WORKERS = 8
_PUSH_TIMEOUT_SECONDS = 10


def _deliver(sub, payload):
    """Send one push. Returns ('sent', None), ('dead', id), or ('error', None)."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            timeout=_PUSH_TIMEOUT_SECONDS,
        )
        return ("sent", None)
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            return ("dead", sub.id)  # subscription expired/unsubscribed
        logger.warning("Web push failed for %s: %s", sub.endpoint[-12:], exc)
        return ("error", None)
    except Exception as exc:  # never let a bad endpoint break a batch
        logger.warning("Web push error: %s", exc)
        return ("error", None)


def send_to_user(user, *, title, body, url="/", tag="mentormind"):
    """Push a notification to every live subscription a user has.

    Sends run concurrently (bounded thread pool) so one slow or unreachable
    endpoint can't serialize the whole batch behind its timeout. Returns the
    number of successful sends; subscriptions the push service rejects as gone
    (404/410) are deleted so the table self-heals.
    """
    if not is_configured():
        return 0

    from concurrent.futures import ThreadPoolExecutor

    from .models import PushSubscription

    subs = list(PushSubscription.objects.filter(user=user))
    if not subs:
        return 0

    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    sent = 0
    dead_ids = []

    workers = min(_MAX_PUSH_WORKERS, len(subs))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for outcome, dead_id in pool.map(lambda s: _deliver(s, payload), subs):
            if outcome == "sent":
                sent += 1
            elif outcome == "dead":
                dead_ids.append(dead_id)

    if dead_ids:
        PushSubscription.objects.filter(id__in=dead_ids).delete()
    return sent
