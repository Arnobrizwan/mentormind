from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.chat.models import ChatMessage
from apps.core.models import Enrollment, QuizAttempt

from .models import PointsEvent
from .services import award_points

# Spamming the chat room must not farm the leaderboard
CHAT_DAILY_POINTS_CAP = 20


@receiver(post_save, sender=Enrollment)
def points_on_enrollment(sender, instance, created, **kwargs):
    if created:
        award_points(instance.student, "enrollment")


@receiver(post_save, sender=QuizAttempt)
def points_on_quiz(sender, instance, created, **kwargs):
    if not created:
        return
    # Only the first attempt on a quiz earns points — retakes are free to
    # learn from but can't be farmed.
    earlier = (
        QuizAttempt.objects.filter(enrollment=instance.enrollment, quiz=instance.quiz)
        .exclude(pk=instance.pk)
        .exists()
    )
    if earlier:
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
    if not created:
        return
    awarded_today = PointsEvent.objects.filter(
        user=instance.sender,
        action="chat_message",
        created_at__date=timezone.localdate(),
    ).count()
    if awarded_today >= CHAT_DAILY_POINTS_CAP:
        return
    award_points(instance.sender, "chat_message")
