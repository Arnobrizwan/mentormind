from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.chat.models import ChatMessage
from apps.core.models import Enrollment, QuizAttempt

from .services import award_points


@receiver(post_save, sender=Enrollment)
def points_on_enrollment(sender, instance, created, **kwargs):
    if created:
        award_points(instance.student, "enrollment")


@receiver(post_save, sender=QuizAttempt)
def points_on_quiz(sender, instance, created, **kwargs):
    if not created:
        return
    award_points(instance.enrollment.student, "quiz_attempt")
    if instance.score == 100:
        award_points(instance.enrollment.student, "quiz_perfect")


@receiver(m2m_changed, sender=Enrollment.completed_lessons.through)
def points_on_lesson_complete(sender, instance, action, pk_set, **kwargs):
    if action == "post_add" and pk_set:
        for _ in pk_set:
            award_points(instance.student, "lesson_completed")


@receiver(post_save, sender=ChatMessage)
def points_on_chat(sender, instance, created, **kwargs):
    if created:
        award_points(instance.sender, "chat_message")
