from rest_framework import permissions


class IsInstructor(permissions.BasePermission):
    """Allows write/update access only to instructors (users in the 'Instructors'

    group), staff members, or superusers.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.groups.filter(name="Instructors").exists()
                or request.user.is_staff
                or request.user.is_superuser
            )
        )


class IsEnrolledStudentOrInstructor(permissions.BasePermission):
    """Allows reading details of course content (like lesson contents or quizzes)

    only if the user is enrolled in the course, or is the course instructor,
    staff, or superuser.
    """

    def has_object_permission(self, request, view, obj):
        # We assume the object is a Course, Lesson, or Enrollment, and we inspect it
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Staff and superusers can do anything
        if user.is_staff or user.is_superuser:
            return True

        from .models import Course, Enrollment, Lesson

        # Resolve the course
        course = None
        if hasattr(obj, "course"):
            course = obj.course
        elif isinstance(obj, Course):
            course = obj

        if isinstance(obj, Enrollment) and obj.student == user:
            return True

        if not course:
            return False

        # Instructors can see their own course content
        if course.instructor == user:
            return True

        # Enrolled students can see course content
        return Enrollment.objects.filter(student=user, course=course).exists()
