from apps.core.models import Course, Enrollment


def can_join_chat(user, course: Course) -> bool:
    """Chat is for enrolled students, the course instructor, and staff."""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser or course.instructor_id == user.id:
        return True
    return Enrollment.objects.filter(student=user, course=course).exists()
