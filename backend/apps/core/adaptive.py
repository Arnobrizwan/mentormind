"""Weak-topic adaptive practice.

Aggregates every per-question quiz result and graded short answer into
per-topic accuracy, then recommends the questions a student should do
next — weakest topics first. Pure ORM + Python: at MentorMind scale a
student has at most a few hundred answered questions, so no
materialised stats table is needed yet.
"""

from collections import defaultdict

from django.db import models

from .models import (
    Enrollment,
    QuizAttempt,
    QuizQuestion,
    ShortAnswerQuestion,
    ShortAnswerSubmission,
)

# Below this accuracy a topic counts as weak; tune per deployment.
WEAK_THRESHOLD_PCT = 80.0
# One lucky/unlucky answer shouldn't brand a topic — require a minimum sample.
MIN_SAMPLES = 2
UNTAGGED = "General"


def topic_stats(user):
    """Per-topic accuracy across quizzes and short answers.

    Returns a list of {topic, accuracy, samples}, weakest first. Quiz
    answers count 0/1; short answers count fractionally (score/max)."""
    correct = defaultdict(float)
    total = defaultdict(float)

    attempts = (
        QuizAttempt.objects.using("default")
        .filter(enrollment__student=user)
        .select_related("quiz")
    )
    for attempt in attempts:
        for detail in (attempt.answers or {}).values():
            if not isinstance(detail, dict):
                continue
            topic = (detail.get("topic") or "").strip() or UNTAGGED
            total[topic] += 1
            if detail.get("correct"):
                correct[topic] += 1

    submissions = (
        ShortAnswerSubmission.objects.using("default")
        .filter(enrollment__student=user)
        .select_related("question")
    )
    for submission in submissions:
        topic = (submission.question.topic or "").strip() or UNTAGGED
        total[topic] += 1
        if submission.max_score:
            correct[topic] += submission.score / submission.max_score

    stats = [
        {
            "topic": topic,
            "accuracy": round(100.0 * correct[topic] / total[topic], 1),
            "samples": int(total[topic]),
        }
        for topic in total
    ]
    stats.sort(key=lambda item: (item["accuracy"], -item["samples"]))
    return stats


def weak_topics(user):
    return [
        item
        for item in topic_stats(user)
        if item["samples"] >= MIN_SAMPLES and item["accuracy"] < WEAK_THRESHOLD_PCT
    ]


def recommendations(user, limit=10):
    """Questions to practise next, drawn from the student's weakest topics
    across their enrolled courses. Quiz questions link back to their quiz;
    short answers to the practice page."""
    weak = weak_topics(user)
    weak_names = [item["topic"] for item in weak]
    course_ids = list(
        Enrollment.objects.using("default")
        .filter(student=user)
        .values_list("course_id", flat=True)
    )
    if not weak_names or not course_ids:
        return {"topics": weak, "recommended": []}

    rank = {name: position for position, name in enumerate(weak_names)}
    untagged_weak = UNTAGGED in rank

    def topic_filter(prefix=""):
        condition = models.Q(**{f"{prefix}topic__in": [t for t in weak_names if t != UNTAGGED]})
        if untagged_weak:
            condition |= models.Q(**{f"{prefix}topic": ""})
        return condition

    items = []
    quiz_questions = (
        QuizQuestion.objects.using("default")
        .filter(quiz__course_id__in=course_ids, quiz__course__is_published=True)
        .filter(topic_filter())
        .select_related("quiz__course")
    )
    for question in quiz_questions:
        items.append(
            {
                "type": "quiz",
                "id": question.id,
                "quiz_id": question.quiz_id,
                "course_slug": question.quiz.course.slug,
                "title": question.quiz.title,
                "preview": question.text[:160],
                "topic": (question.topic or "").strip() or UNTAGGED,
            }
        )

    short_answers = (
        ShortAnswerQuestion.objects.using("default")
        .filter(course_id__in=course_ids, is_published=True, course__is_published=True)
        .filter(topic_filter())
        .select_related("course")
    )
    for question in short_answers:
        items.append(
            {
                "type": "short_answer",
                "id": question.id,
                "course_slug": question.course.slug,
                "title": "Short-answer practice",
                "preview": question.prompt[:160],
                "topic": (question.topic or "").strip() or UNTAGGED,
            }
        )

    items.sort(key=lambda item: rank.get(item["topic"], len(rank)))
    return {"topics": weak, "recommended": items[:limit]}
