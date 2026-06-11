"""Study-plan composition + the weekly agentic sweep.

A plan pulls together, per student:
1. due flashcards (revision queue)
2. weakest topics (adaptive practice)
3. the next unfinished lesson per course
4. quizzes not yet attempted

The weekly sweep also *acts* on neglect: two consecutive weeks under the
completion floor opens a medium-risk RemediationTicket so a human
follows up — the planner escalates before the dropout model has to.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import Enrollment, Lesson, Quiz, QuizAttempt

from .models import StudyPlan

logger = logging.getLogger(__name__)

MAX_LESSON_ITEMS = 3
MAX_QUIZ_ITEMS = 2
MAX_TOPIC_ITEMS = 2
# Below this completion two weeks running, a human gets a ticket.
SLIPPING_FLOOR_PCT = 30.0


def week_start(today=None):
    today = today or timezone.localdate()
    return today - timedelta(days=today.weekday())


def build_items(user):
    items = []

    def add(kind, title, detail="", link=""):
        items.append(
            {
                "id": len(items) + 1,
                "kind": kind,
                "title": title,
                "detail": detail,
                "link": link,
                "done": False,
            }
        )

    enrollments = list(
        Enrollment.objects.using("default")
        .filter(student=user)
        .select_related("course")
        .prefetch_related("completed_lessons")
    )
    course_ids = [e.course_id for e in enrollments]

    # 1. Due flashcards
    try:
        from apps.revision.models import ReviewCard

        due = (
            ReviewCard.objects.using("default")
            .filter(
                user=user,
                due_at__lte=timezone.now(),
                flashcard__is_published=True,
                flashcard__course_id__in=course_ids,
            )
            .count()
        )
        if due:
            add(
                "revision",
                f"Clear your {due} due flashcard{'s' if due != 1 else ''}",
                "Spaced repetition works best when reviews don't pile up.",
                "/revision",
            )
    except Exception:  # revision tables may not exist mid-migration
        logger.debug("revision queue unavailable while building plan")

    # 2. Weak topics
    from apps.core.adaptive import weak_topics

    for topic in weak_topics(user)[:MAX_TOPIC_ITEMS]:
        add(
            "practice",
            f"Practise {topic['topic']}",
            f"Your accuracy here is {topic['accuracy']}% — bring it above 80%.",
            # Focus areas on the dashboard carry the per-question links.
            "/dashboard",
        )

    # 3. Next lesson per course
    lesson_items = 0
    for enrollment in enrollments:
        if lesson_items >= MAX_LESSON_ITEMS:
            break
        done_ids = {lesson.id for lesson in enrollment.completed_lessons.all()}
        next_lesson = (
            Lesson.objects.using("default")
            .filter(course=enrollment.course, is_published=True)
            .exclude(id__in=done_ids)
            .order_by("order")
            .first()
        )
        if next_lesson:
            add(
                "lesson",
                f"Continue {enrollment.course.title}: {next_lesson.title}",
                "",
                f"/courses/{enrollment.course.slug}",
            )
            lesson_items += 1

    # 4. Unattempted quizzes
    attempted = set(
        QuizAttempt.objects.using("default")
        .filter(enrollment__student=user)
        .values_list("quiz_id", flat=True)
    )
    fresh_quizzes = (
        Quiz.objects.using("default")
        .filter(course_id__in=course_ids, course__is_published=True)
        .exclude(id__in=attempted)
        .select_related("course")[:MAX_QUIZ_ITEMS]
    )
    for quiz in fresh_quizzes:
        add(
            "quiz",
            f"Take the quiz: {quiz.title}",
            "",
            f"/courses/{quiz.course.slug}",
        )

    return items


def ensure_plan(user):
    """This week's plan, building it on first access."""
    monday = week_start()
    plan = (
        StudyPlan.objects.using("default")
        .filter(student=user, week_start=monday)
        .first()
    )
    if plan is None:
        # get_or_create rides the (student, week_start) unique constraint,
        # so concurrent first accesses can't race into an IntegrityError.
        plan, _ = StudyPlan.objects.using("default").get_or_create(
            student=user,
            week_start=monday,
            defaults={"items": build_items(user)},
        )
    return plan


def _escalate_if_slipping(user, monday):
    """Two consecutive past weeks under the floor → one medium ticket."""
    previous = list(
        StudyPlan.objects.using("default")
        .filter(student=user, week_start__lt=monday)
        .order_by("-week_start")[:2]
    )
    if len(previous) < 2:
        return False
    if any(not plan.items for plan in previous):
        return False
    if any(plan.completion_pct >= SLIPPING_FLOOR_PCT for plan in previous):
        return False

    from apps.engagement.models import RemediationTicket

    has_unresolved = (
        RemediationTicket.objects.using("default")
        .filter(
            student=user,
            status__in=[
                RemediationTicket.Status.OPEN,
                RemediationTicket.Status.CONTACTED,
            ],
        )
        .exists()
    )
    if has_unresolved:
        return False
    from django.db import IntegrityError

    try:
        RemediationTicket.objects.using("default").create(
            student=user,
            risk=RemediationTicket.Risk.MEDIUM,
            probability=0.0,
            features={
                "source": "study_plan",
                "recent_completion_pct": [plan.completion_pct for plan in previous],
            },
        )
    except IntegrityError:
        # A concurrent risk scan opened a ticket first — that's the goal
        # achieved, not a failure.
        return False
    return True


def build_weekly_plans():
    """The Monday sweep: a fresh plan + nudge for every active enrolled
    student, with slipping-streak escalation. Returns (built, escalated)."""
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    User = get_user_model()
    monday = week_start()
    built = escalated = 0
    students = (
        User.objects.filter(is_active=True, enrollments__isnull=False)
        .distinct()
        .order_by("id")
    )
    for user in students.iterator():
        _, created = StudyPlan.objects.using("default").get_or_create(
            student=user,
            week_start=monday,
            defaults={"items": build_items(user)},
        )
        if created:
            built += 1
            notify(
                user,
                Notification.Kind.SYSTEM,
                title="Your study plan for this week is ready 📋",
                body="A fresh plan tuned to your weak topics and due revision "
                "is waiting on your dashboard.",
                link="/planner",
            )
        if _escalate_if_slipping(user, monday):
            escalated += 1
    return built, escalated
