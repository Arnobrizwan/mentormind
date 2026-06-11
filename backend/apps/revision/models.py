"""Spaced-repetition revision — flashcards + per-student SM-2 schedules.

Flashcards belong to a course (optionally a lesson). They're drafted by
the ml-service generator or written by hand, and only published cards
ever reach students. Each student gets one ReviewCard per flashcard
holding their personal SM-2 state.
"""

from django.contrib.auth import get_user_model
from django.db import models

from apps.core.models import Course, Lesson

User = get_user_model()


class Flashcard(models.Model):
    """One front/back revision card. Drafts (is_published=False) sit in the
    instructor's review queue until approved — AI output is never shown to
    students unreviewed."""

    class Source(models.TextChoices):
        LLM = "llm", "AI-generated"
        HEURISTIC = "heuristic", "Auto-extracted"
        INSTRUCTOR = "instructor", "Instructor-written"

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="flashcards"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="flashcards",
    )
    topic = models.CharField(max_length=100, blank=True)
    front = models.TextField(help_text="The prompt side — a question or cue.")
    back = models.TextField(help_text="The answer side.")
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.INSTRUCTOR
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["course", "is_published"])]

    def __str__(self):
        return f"[{self.course.title}] {self.front[:60]}"


class ReviewCard(models.Model):
    """A student's SM-2 state for one flashcard. Created lazily the first
    time the card enters their queue; due immediately on creation."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="review_cards"
    )
    flashcard = models.ForeignKey(
        Flashcard, on_delete=models.CASCADE, related_name="review_cards"
    )
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.FloatField(default=0)
    repetitions = models.PositiveIntegerField(default=0)
    due_at = models.DateTimeField()
    last_grade = models.PositiveIntegerField(blank=True, null=True)
    reviews_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "flashcard")
        indexes = [models.Index(fields=["user", "due_at"])]

    def __str__(self):
        return f"{self.user.email} · card {self.flashcard_id} · due {self.due_at:%Y-%m-%d}"
