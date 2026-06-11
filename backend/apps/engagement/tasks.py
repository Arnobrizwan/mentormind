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
