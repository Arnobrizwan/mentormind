from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Course, Lesson, Quiz
from .services import invalidate_course_cache


@receiver(post_save, sender=Course)
@receiver(post_delete, sender=Course)
def on_course_change(sender, instance, **kwargs):
    invalidate_course_cache(instance.id, instance.slug)


@receiver(post_save, sender=Lesson)
@receiver(post_delete, sender=Lesson)
def on_lesson_change(sender, instance, **kwargs):
    # Invalidate parent course cache
    invalidate_course_cache(instance.course_id, instance.course.slug)


@receiver(post_save, sender=Quiz)
@receiver(post_delete, sender=Quiz)
def on_quiz_change(sender, instance, **kwargs):
    # Invalidate parent course cache
    invalidate_course_cache(instance.course_id, instance.course.slug)
