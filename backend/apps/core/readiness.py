"""Exam-readiness scoring — one motivating number per enrollment.

Blends four signals into 0-100:
- syllabus progress (lessons completed)          40%
- quiz average                                   30%
- practice volume (attempts/answers/reviews)     15%
- answer accuracy across everything attempted    15%

Weights are deliberate defaults, overridable live via SiteSettings
(readiness-weight-progress etc., integers summing to 100).
"""

from django.db import models as dj_models

from .models import Lesson, QuizAttempt, ShortAnswerSubmission

# Practice volume saturates here — more reps than this stop adding score.
FULL_PRACTICE_VOLUME = 20

DEFAULT_WEIGHTS = {
    "progress": 40,
    "quiz": 30,
    "practice": 15,
    "accuracy": 15,
}


def _weights():
    from apps.settings_engine.services import get_setting

    weights = {}
    for key, default in DEFAULT_WEIGHTS.items():
        configured = get_setting(f"readiness-weight-{key}")
        weights[key] = configured if isinstance(configured, int) and configured >= 0 else default
    total = sum(weights.values()) or 1
    return weights, total


def enrollment_readiness(enrollment):
    """Score one enrollment. Returns {readiness, components}."""
    course = enrollment.course
    student = enrollment.student

    total_lessons = (
        Lesson.objects.using("default")
        .filter(course=course, is_published=True)
        .count()
    )
    completed = enrollment.completed_lessons.using("default").count()
    progress = 100.0 * completed / total_lessons if total_lessons else 0.0

    attempts = list(
        QuizAttempt.objects.using("default").filter(enrollment=enrollment)
    )
    quiz_avg = sum(a.score for a in attempts) / len(attempts) if attempts else 0.0

    submissions = list(
        ShortAnswerSubmission.objects.using("default").filter(enrollment=enrollment)
    )
    review_count = 0
    try:
        from apps.revision.models import ReviewCard

        review_count = (
            ReviewCard.objects.using("default")
            .filter(user=student, flashcard__course=course)
            .aggregate(total=dj_models.Sum("reviews_count"))["total"]
            or 0
        )
    except Exception:  # revision app optional at runtime
        pass
    volume = len(attempts) + len(submissions) + review_count
    practice = 100.0 * min(volume, FULL_PRACTICE_VOLUME) / FULL_PRACTICE_VOLUME

    # Accuracy: per-question quiz results + fractional short-answer scores
    correct = total = 0.0
    for attempt in attempts:
        for detail in (attempt.answers or {}).values():
            if isinstance(detail, dict):
                total += 1
                if detail.get("correct"):
                    correct += 1
    for submission in submissions:
        total += 1
        if submission.max_score:
            correct += submission.score / submission.max_score
    accuracy = 100.0 * correct / total if total else 0.0

    weights, weight_total = _weights()
    readiness = (
        progress * weights["progress"]
        + quiz_avg * weights["quiz"]
        + practice * weights["practice"]
        + accuracy * weights["accuracy"]
    ) / weight_total

    return {
        "readiness": round(readiness, 1),
        "components": {
            "progress_pct": round(progress, 1),
            "quiz_avg": round(quiz_avg, 1),
            "practice_volume": round(practice, 1),
            "accuracy": round(accuracy, 1),
        },
    }


def student_readiness(user):
    """Readiness for each of the student's enrollments."""
    from .models import Enrollment

    results = []
    enrollments = (
        Enrollment.objects.using("default")
        .filter(student=user)
        .select_related("course")
    )
    for enrollment in enrollments:
        entry = enrollment_readiness(enrollment)
        entry.update(
            {
                "course": enrollment.course_id,
                "course_slug": enrollment.course.slug,
                "course_title": enrollment.course.title,
            }
        )
        results.append(entry)
    results.sort(key=lambda item: item["readiness"])
    return results


def course_readiness(course):
    """Every enrolled student's readiness — the instructor's view."""
    from .models import Enrollment

    results = []
    enrollments = (
        Enrollment.objects.using("default")
        .filter(course=course)
        .select_related("student")
    )
    for enrollment in enrollments:
        entry = enrollment_readiness(enrollment)
        entry.update(
            {
                "enrollment": enrollment.id,
                "student_email": enrollment.student.email,
                "student_name": enrollment.student.display_name,
            }
        )
        results.append(entry)
    results.sort(key=lambda item: item["readiness"])
    return results
