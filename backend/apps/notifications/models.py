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


class PushSubscription(models.Model):
    """A browser Web Push subscription for PWA reminders. One user can have
    several (laptop, phone, …). Dead endpoints are pruned on send when the
    push service replies 404/410."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    # The push service endpoint URL — unique per browser subscription.
    endpoint = models.URLField(max_length=500, unique=True)
    # Keys from PushSubscription.toJSON().keys (browser-supplied).
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user"])]

    def __str__(self):
        return f"push:{self.user.email}:{self.endpoint[-12:]}"
