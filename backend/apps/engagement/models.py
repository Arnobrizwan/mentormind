from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class PointsEvent(models.Model):
    """One ledger row per points-earning action — the source of truth for
    totals, streaks and the weekly leaderboard."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="points_events")
    action = models.CharField(max_length=40)
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user.email} +{self.points} ({self.action})"


class DailyActivity(models.Model):
    """One row per user per active day — streaks are computed from this."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="active_days")
    date = models.DateField()

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]


class Badge(models.Model):
    """Badges are DB rows, not code — add/edit conditions live from the
    admin without redeploying (dynamic-first)."""

    class Rule(models.TextChoices):
        POINTS_TOTAL = "points_total", "Total points"
        QUIZZES_TAKEN = "quizzes_taken", "Quizzes taken"
        PERFECT_QUIZZES = "perfect_quizzes", "Perfect quiz scores"
        LESSONS_COMPLETED = "lessons_completed", "Lessons completed"
        STREAK_DAYS = "streak_days", "Day streak"
        ENROLLMENTS = "enrollments", "Courses enrolled"
        CHAT_MESSAGES = "chat_messages", "Chat messages sent"
        TUTOR_QUESTIONS = "tutor_questions", "AI tutor questions asked"

    key = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=8, default="🏅")
    rule = models.CharField(max_length=30, choices=Rule.choices)
    threshold = models.PositiveIntegerField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "threshold"]

    def __str__(self):
        return f"{self.icon} {self.name}"


class AwardedBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="awarded_badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="awards")
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")
