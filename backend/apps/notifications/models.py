from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Notification(models.Model):
    """An in-app notification, optionally mirrored to email by a Celery task."""

    class Kind(models.TextChoices):
        ENROLLMENT = "enrollment", "Enrollment"
        QUIZ_RESULT = "quiz_result", "Quiz result"
        PROCTORING = "proctoring", "Proctoring alert"
        RISK = "risk", "Dropout risk"
        SYSTEM = "system", "System"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=40, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True, help_text="Frontend route, e.g. /courses/foo")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{self.user.email}: {self.title}"
