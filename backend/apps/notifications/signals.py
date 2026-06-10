from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.models import Enrollment, QuizAttempt

from .models import Notification
from .services import notify


@receiver(post_save, sender=Enrollment)
def on_enrollment(sender, instance, created, **kwargs):
    if not created:
        return
    notify(
        instance.student,
        Notification.Kind.ENROLLMENT,
        f"Welcome to {instance.course.title}",
        f"You are enrolled. {instance.course.lessons.count()} lesson(s) await.",
        link=f"/courses/{instance.course.slug}",
    )
    notify(
        instance.course.instructor,
        Notification.Kind.ENROLLMENT,
        f"New student in {instance.course.title}",
        f"{instance.student.display_name or instance.student.email} just enrolled.",
        link=f"/courses/{instance.course.slug}",
    )


@receiver(post_save, sender=QuizAttempt)
def on_quiz_attempt(sender, instance, created, **kwargs):
    if not created:
        return
    notify(
        instance.enrollment.student,
        Notification.Kind.QUIZ_RESULT,
        f"You scored {instance.score}% on {instance.quiz.title}",
        f"{instance.correct_answers} of {instance.total_questions} correct.",
        link=f"/courses/{instance.quiz.course.slug}",
    )
