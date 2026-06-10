from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class TutorSession(models.Model):
    """One AI-tutor conversation, resumable across visits."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tutor_sessions")
    subject = models.CharField(max_length=80, blank=True)
    level = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.email}: {self.title or self.subject or 'session'}"


class TutorMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    session = models.ForeignKey(TutorSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    # +1 thumbs up, -1 thumbs down, null = no feedback yet
    feedback = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["session", "created_at"])]
