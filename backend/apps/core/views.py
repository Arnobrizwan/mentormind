from django.conf import settings
from django.core.cache import cache
from django.db import connections, models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Course, Enrollment, Lesson, Quiz, QuizAttempt, QuizQuestion
from .permissions import IsInstructor, IsEnrolledStudentOrInstructor
from .serializers import (
    CourseSerializer,
    EnrollmentSerializer,
    LessonSerializer,
    QuizSerializer,
    QuizAttemptSerializer,
)


class HealthView(APIView):
    """Liveness + dependency health. Used by nginx, K8s probes and UptimeRobot."""

    permission_classes = [AllowAny]

    def get(self, request):
        checks = {"instance": settings.INSTANCE_NAME}

        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception as exc:  # pragma: no cover - only on infra failure
            checks["database"] = f"error: {exc}"

        if "replica" in connections:
            try:
                with connections["replica"].cursor() as cursor:
                    cursor.execute("SELECT 1")
                checks["replica"] = "ok"
            except Exception as exc:  # pragma: no cover
                checks["replica"] = f"error: {exc}"

        try:
            cache.set("health_ping", "pong", 5)
            checks["cache"] = "ok" if cache.get("health_ping") == "pong" else "error"
        except Exception as exc:  # pragma: no cover
            checks["cache"] = f"error: {exc}"

        healthy = all(v == "ok" for k, v in checks.items() if k != "instance")
        return Response(checks, status=200 if healthy else 503)


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet for instructors to manage courses, and students to list/view them."""

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    lookup_field = "slug"

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        if self.action == "enroll":
            return [IsAuthenticated()]
        return [IsInstructor()]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Course.objects.filter(is_published=True).select_related("instructor")

        # Instructors can see all published courses + their own drafts
        if (
            user.groups.filter(name="Instructors").exists()
            or user.is_staff
            or user.is_superuser
        ):
            return (
                Course.objects.filter(
                    models.Q(is_published=True) | models.Q(instructor=user)
                )
                .select_related("instructor")
                .distinct()
            )

        return Course.objects.filter(is_published=True).select_related("instructor")

    def list(self, request, *args, **kwargs):
        # Cache list of published courses only when no filters or user drafts are requested
        user = request.user
        is_instructor = (
            user
            and user.is_authenticated
            and (
                user.groups.filter(name="Instructors").exists()
                or user.is_staff
                or user.is_superuser
            )
        )

        if not request.query_params and not is_instructor:
            courses = services.get_published_courses()
            page = self.paginate_queryset(courses)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(courses, many=True)
            return Response(serializer.data)

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        # Fetch from cache first
        lookup_val = self.kwargs[self.lookup_field]
        course = services.get_course_detail(lookup_val)

        if not course:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not course.is_published:
            user = request.user
            if not user or not user.is_authenticated or not (
                user.is_staff or user.is_superuser or course.instructor == user
            ):
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(course)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="enroll",
    )
    def enroll(self, request, slug=None):
        """Enroll the current user in this course."""
        course = self.get_object()

        if (
            not course.is_published
            and course.instructor != request.user
            and not request.user.is_staff
        ):
            return Response(
                {"error": "Cannot enroll in an unpublished course."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Strongly consistent write-then-read
        enrollment, created = Enrollment.objects.using("default").get_or_create(
            student=request.user, course=course
        )

        serializer = EnrollmentSerializer(enrollment, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class LessonViewSet(viewsets.ModelViewSet):
    """ViewSet to manage individual lessons under a course."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), IsEnrolledStudentOrInstructor()]
        return [IsInstructor()]

    def get_queryset(self):
        user = self.request.user
        # Filter lessons based on active course filtering or enrollment
        queryset = Lesson.objects.select_related("course")

        # If user is instructor/staff, show draft and published
        if user.is_staff or user.is_superuser or user.groups.filter(name="Instructors").exists():
            return queryset

        # Standard students only see published lessons in enrolled/published courses
        return queryset.filter(is_published=True)

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if course.instructor != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You are not the instructor of this course.")
        serializer.save()


class QuizViewSet(viewsets.ModelViewSet):
    """ViewSet for instructors to manage quizzes and students to view/submit them."""

    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "submit"]:
            return [IsAuthenticated(), IsEnrolledStudentOrInstructor()]
        return [IsInstructor()]

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if course.instructor != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You are not the instructor of this course.")
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit(self, request, pk=None):
        """Submit quiz answers, calculate score, and record attempt."""
        quiz = self.get_object()
        user = request.user

        # Fetch enrollment to check eligibility (strongly consistent write-your-own-writes)
        enrollment = Enrollment.objects.using("default").filter(student=user, course=quiz.course).first()
        if not enrollment:
            return Response(
                {"error": "You must be enrolled in the course to attempt the quiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        questions = quiz.questions.using("default").all()
        total_questions = questions.count()
        if total_questions == 0:
            return Response(
                {"error": "This quiz does not have any questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submitted_answers = request.data.get("answers", {})
        correct_answers = 0
        for q in questions:
            ans = submitted_answers.get(str(q.id), submitted_answers.get(q.id))
            if ans is not None and int(ans) == q.correct_option_index:
                correct_answers += 1

        score = round((correct_answers / total_questions) * 100, 2)

        attempt = QuizAttempt.objects.using("default").create(
            enrollment=enrollment,
            quiz=quiz,
            score=score,
            total_questions=total_questions,
            correct_answers=correct_answers,
        )

        serializer = QuizAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    """ReadOnly viewset for students to view their course enrollments and progress."""

    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Always fetch from default db for own enrollment listings to prevent replica lag issues
        return (
            Enrollment.objects.using("default")
            .filter(student=self.request.user)
            .select_related("course")
            .prefetch_related("completed_lessons", "quiz_attempts")
        )

    @action(detail=True, methods=["post"], url_path="complete-lesson")
    def complete_lesson(self, request, pk=None):
        """Mark a lesson as completed for the enrollment."""
        enrollment = self.get_object()

        if enrollment.student != request.user and not request.user.is_staff:
            return Response(
                {"error": "You do not have permission to modify this enrollment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        lesson_id = request.data.get("lesson_id")
        if not lesson_id:
            return Response(
                {"error": "lesson_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lesson = Lesson.objects.using("default").get(id=lesson_id, course=enrollment.course)
        except Lesson.DoesNotExist:
            return Response(
                {"error": "Lesson not found in this course."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrollment.completed_lessons.add(lesson)

        serializer = self.get_serializer(enrollment)
        return Response(serializer.data, status=status.HTTP_200_OK)
