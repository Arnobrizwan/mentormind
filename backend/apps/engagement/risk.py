"""Dropout-risk remediation — closing the loop on the prediction model.

The weekly Celery scan computes each active student's engagement features,
asks the ml-service /v1/predict/dropout-risk for a score, and for high-risk
students: sends an automated encouragement nudge (in-app + email mirror)
and opens a RemediationTicket for a human instructor to work from the
Student Success view.
"""

import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.chat.models import ChatMessage
from apps.core import ml_client
from apps.core.models import Enrollment, Lesson, QuizAttempt

from .models import RemediationTicket

logger = logging.getLogger(__name__)


def engagement_features(user):
    """The exact feature vector the dropout model was trained on —
    keep field names in lockstep with ml-service EngagementFeatures."""
    now = timezone.now()
    enrollments = list(
        Enrollment.objects.using("default")
        .filter(student=user)
        .prefetch_related("completed_lessons")
    )

    progress_values = []
    completed_total = 0
    for enrollment in enrollments:
        total = Lesson.objects.using("default").filter(
            course=enrollment.course, is_published=True
        ).count()
        completed = enrollment.completed_lessons.count()
        completed_total += completed
        if total:
            progress_values.append(100.0 * completed / total)
    progress_pct = sum(progress_values) / len(progress_values) if progress_values else 0.0

    last_seen = user.last_login or user.date_joined
    days_since_last_login = max(0.0, (now - last_seen).total_seconds() / 86400)

    quiz_avg = 0.0
    attempts = QuizAttempt.objects.using("default").filter(enrollment__student=user)
    if attempts.exists():
        quiz_avg = sum(a.score for a in attempts) / attempts.count()

    first_enrolled = min((e.enrolled_at for e in enrollments), default=now)
    weeks_enrolled = max(1.0, (now - first_enrolled).total_seconds() / (86400 * 7))
    lessons_per_week = completed_total / weeks_enrolled

    chat_messages = ChatMessage.objects.using("default").filter(sender=user).count()

    return {
        "progress_pct": round(progress_pct, 2),
        "days_since_last_login": round(days_since_last_login, 2),
        "quiz_avg": round(quiz_avg, 2),
        "lessons_per_week": round(lessons_per_week, 3),
        "chat_messages": float(chat_messages),
    }


def remediate(user, risk, probability, features):
    """Open (or refresh) the student's ticket and send the encouragement
    nudge. Idempotent per scan: an existing unresolved ticket is updated,
    not duplicated, and the nudge only goes out with a fresh ticket."""
    unresolved = (
        RemediationTicket.objects.using("default")
        .filter(
            student=user,
            status__in=[
                RemediationTicket.Status.OPEN,
                RemediationTicket.Status.CONTACTED,
            ],
        )
        .first()
    )
    created = unresolved is None
    if unresolved:
        ticket = unresolved
        ticket.risk = risk
        ticket.probability = probability
        ticket.features = features
        ticket.save(update_fields=["risk", "probability", "features", "updated_at"])
    else:
        ticket = RemediationTicket.objects.using("default").create(
            student=user, risk=risk, probability=probability, features=features
        )
    if created:
        from apps.notifications.models import Notification
        from apps.notifications.services import notify

        notify(
            user,
            Notification.Kind.RISK,
            title="We miss you at MentorMind! 🌱",
            body=(
                "It's been a little while — your courses are waiting for you. "
                "Jump back in with a quick lesson, or ask the AI tutor "
                "anything you're stuck on. Small steps count!"
            ),
            link="/dashboard",
        )
    return ticket, created


def scan_students():
    """Score every active enrolled student. Returns (scanned, flagged)."""
    User = get_user_model()
    students = (
        User.objects.filter(is_active=True, enrollments__isnull=False)
        .distinct()
        .order_by("id")
    )
    scanned = flagged = 0
    for user in students.iterator():
        features = engagement_features(user)
        try:
            result = ml_client.post_json("/v1/predict/dropout-risk", features)
        except ml_client.MLServiceError as exc:
            logger.warning("dropout-risk scoring failed for user %s: %s", user.id, exc)
            continue
        scanned += 1
        if result.get("risk") == "high":
            flagged += 1
            remediate(
                user,
                RemediationTicket.Risk.HIGH,
                float(result.get("probability", 0.0)),
                features,
            )
    return scanned, flagged
