from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.settings_engine.services import get_setting

from .models import AwardedBadge, Badge, DailyActivity, PointsEvent

# Defaults only — operators override any of these live by creating a
# SiteSetting row named points-<action> in the admin console.
DEFAULT_POINT_VALUES = {
    "daily_login": 5,
    "enrollment": 10,
    "lesson_completed": 5,
    "quiz_attempt": 10,
    "quiz_perfect": 15,
    "chat_message": 1,
    "tutor_question": 2,
    "daily_challenge": 20,
}


def point_value(action):
    configured = get_setting(f"points-{action}")
    if isinstance(configured, int):
        return configured
    return DEFAULT_POINT_VALUES.get(action, 0)


def award_points(user, action, points=None):
    """Append to the ledger, mark the day active, re-check badges."""
    value = point_value(action) if points is None else points
    if value == 0:
        return None
    event = PointsEvent.objects.create(user=user, action=action, points=value)
    DailyActivity.objects.get_or_create(user=user, date=timezone.localdate())
    check_badges(user)
    return event


def total_points(user):
    return PointsEvent.objects.filter(user=user).aggregate(t=Sum("points"))["t"] or 0


def current_streak(user):
    """Consecutive active days ending today or yesterday."""
    dates = set(
        DailyActivity.objects.filter(user=user).values_list("date", flat=True)[:400]
    )
    if not dates:
        return 0
    day = timezone.localdate()
    if day not in dates:
        day -= timedelta(days=1)  # today not active yet — streak still alive
    streak = 0
    while day in dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def claim_daily_login(user):
    """Idempotent once-per-day login reward."""
    today = timezone.localdate()
    already = PointsEvent.objects.filter(
        user=user, action="daily_login", created_at__date=today
    ).exists()
    if already:
        return False, 0
    event = award_points(user, "daily_login")
    return True, event.points if event else 0


def daily_login_claimed(user):
    return PointsEvent.objects.filter(
        user=user, action="daily_login", created_at__date=timezone.localdate()
    ).exists()


def weekly_leaderboard(limit=10):
    since = timezone.now() - timedelta(days=7)
    rows = (
        PointsEvent.objects.filter(created_at__gte=since)
        .values("user_id", "user__display_name", "user__email")
        .annotate(points=Sum("points"))
        .order_by("-points")[:limit]
    )
    return [
        {
            "rank": rank,
            "student": row["user__display_name"] or row["user__email"].split("@")[0],
            "points": row["points"],
        }
        for rank, row in enumerate(rows, start=1)
    ]


# --- Badges -----------------------------------------------------------------


def _metric(user, rule):
    from apps.chat.models import ChatMessage
    from apps.core.models import Enrollment, QuizAttempt
    from apps.tutor.models import TutorMessage

    if rule == Badge.Rule.POINTS_TOTAL:
        return total_points(user)
    if rule == Badge.Rule.QUIZZES_TAKEN:
        return QuizAttempt.objects.filter(enrollment__student=user).count()
    if rule == Badge.Rule.PERFECT_QUIZZES:
        return QuizAttempt.objects.filter(enrollment__student=user, score=100).count()
    if rule == Badge.Rule.LESSONS_COMPLETED:
        return sum(
            e.completed_lessons.count()
            for e in Enrollment.objects.filter(student=user).prefetch_related(
                "completed_lessons"
            )
        )
    if rule == Badge.Rule.STREAK_DAYS:
        return current_streak(user)
    if rule == Badge.Rule.ENROLLMENTS:
        return Enrollment.objects.filter(student=user).count()
    if rule == Badge.Rule.CHAT_MESSAGES:
        return ChatMessage.objects.filter(sender=user).count()
    if rule == Badge.Rule.TUTOR_QUESTIONS:
        return TutorMessage.objects.filter(session__user=user, role="user").count()
    return 0


def check_badges(user):
    """Award any badges whose threshold the user has now crossed."""
    earned_ids = set(
        AwardedBadge.objects.filter(user=user).values_list("badge_id", flat=True)
    )
    fresh = []
    for badge in Badge.objects.exclude(id__in=earned_ids):
        if _metric(user, badge.rule) >= badge.threshold:
            AwardedBadge.objects.get_or_create(user=user, badge=badge)
            fresh.append(badge)
    return fresh


def badge_progress(user):
    """All badges with earned state and a progress hint for locked ones."""
    earned = {
        ab.badge_id: ab.awarded_at
        for ab in AwardedBadge.objects.filter(user=user)
    }
    entries = []
    for badge in Badge.objects.all():
        current = _metric(user, badge.rule)
        remaining = max(0, badge.threshold - current)
        entries.append(
            {
                "key": badge.key,
                "name": badge.name,
                "description": badge.description,
                "icon": badge.icon,
                "earned": badge.id in earned,
                "progress": min(current, badge.threshold),
                "threshold": badge.threshold,
                "hint": None if badge.id in earned else f"{remaining} more to go",
            }
        )
    return entries
