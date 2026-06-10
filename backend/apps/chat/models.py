from django.contrib.auth import get_user_model
from django.db import models

from apps.core.models import Course

User = get_user_model()


class ChatMessage(models.Model):
    """A message in a course's live chat room."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="chat_messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_messages")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["course", "created_at"])]

    def __str__(self):
        return f"{self.sender.email} in {self.course.slug}: {self.body[:30]}"
