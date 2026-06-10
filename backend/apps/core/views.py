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
from .permissions import IsEnrolledStudentOrInstructor, IsInstructor, is_instructor
from .serializers import (
    CourseSerializer,
    EnrollmentSerializer,
    LessonSerializer,
    QuizSerializer,
    QuizAttemptSerializer,
    QuizQuestionSerializer,
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
        if self.action in ["list", "retrieve", "leaderboard"]:
            return [AllowAny()]
        if self.action in ["enroll", "recommended"]:
            return [IsAuthenticated()]
        return [IsInstructor()]

    def get_queryset(self):
        user = self.request.user
        # Instructors can see all published courses + their own drafts
        if is_instructor(user):
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
        if not request.query_params and not is_instructor(request.user):
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

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def leaderboard(self, request, slug=None):
        """Top quiz scorers — Redis sorted set when available, DB fallback."""
        course = self.get_object()
        return Response(services.get_leaderboard(course.id))

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def recommended(self, request):
        """Personalised course picks via enrollment co-occurrence.
        Flag-gated: flip 'recommendations' off in the admin console to
        disable the feature live (absent flag means enabled)."""
        from apps.flags.services import flag_enabled

        if not flag_enabled("recommendations", default=True):
            return Response(
                {"detail": "Recommendations are currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
        courses = services.get_recommendations(request.user)
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[IsInstructor])
    def students(self, request, slug=None):
        """Roster with progress — only for this course's instructor/staff."""
        course = self.get_object()
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only this course's instructor can view its roster."},
                status=status.HTTP_403_FORBIDDEN,
            )
        enrollments = (
            Enrollment.objects.using("default")
            .filter(course=course)
            .select_related("student")
            .prefetch_related("completed_lessons", "quiz_attempts")
            .order_by("-enrolled_at")
        )
        serializer = EnrollmentSerializer(
            enrollments, many=True, context={"request": request}
        )
        return Response(serializer.data)


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
        if is_instructor(user):
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


class SystemStatusView(APIView):
    """Aggregate live status of every architectural component — feeds the
    /system page. Public by design: this project is a system-design showcase."""

    permission_classes = [AllowAny]

    def get(self, request):
        components = {}

        def probe(name, fn):
            import time

            start = time.monotonic()
            try:
                fn()
                components[name] = {"status": "ok"}
            except Exception as exc:
                components[name] = {"status": "error", "detail": str(exc)[:160]}
            components[name]["latency_ms"] = round((time.monotonic() - start) * 1000, 1)

        def check_db(alias):
            def _check():
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")

            return _check

        probe("database_primary", check_db("default"))
        if "replica" in connections:
            probe("database_replica", check_db("replica"))
        else:
            components["database_replica"] = {"status": "not_configured"}

        def check_cache():
            cache.set("system_ping", "pong", 5)
            assert cache.get("system_ping") == "pong"

        probe("cache", check_cache)

        if settings.CELERY_TASK_ALWAYS_EAGER:
            components["celery"] = {"status": "eager_mode"}
        else:
            def check_celery():
                from config.celery import app as celery_app

                with celery_app.connection_for_read() as conn:
                    conn.ensure_connection(max_retries=1, timeout=2)

            probe("celery_broker", check_celery)

        ml_url = getattr(settings, "ML_SERVICE_URL", "")
        if ml_url:
            def check_ml():
                import urllib.request

                with urllib.request.urlopen(f"{ml_url.rstrip('/')}/healthz", timeout=2) as res:
                    assert res.status == 200

            probe("ml_service", check_ml)
        else:
            components["ml_service"] = {"status": "not_configured"}

        healthy = all(
            c["status"] in ("ok", "eager_mode", "not_configured")
            for c in components.values()
        )
        return Response(
            {
                "instance": settings.INSTANCE_NAME,
                "healthy": healthy,
                "components": components,
            },
            status=200 if healthy else 503,
        )


class QuizQuestionViewSet(viewsets.ModelViewSet):
    """Question authoring for instructors — ownership enforced through the
    parent quiz's course."""

    serializer_class = QuizQuestionSerializer
    permission_classes = [IsInstructor]
    filterset_fields = ["quiz"]

    def get_queryset(self):
        queryset = QuizQuestion.objects.using("default").select_related("quiz__course")
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return queryset
        return queryset.filter(quiz__course__instructor=user)

    def perform_create(self, serializer):
        quiz = serializer.validated_data["quiz"]
        user = self.request.user
        if quiz.course.instructor != user and not user.is_staff:
            raise PermissionDenied("You are not the instructor of this course.")
        serializer.save()


class SearchView(APIView):
    """Title/description search across published courses and lessons."""

    permission_classes = [AllowAny]

    def get(self, request):
        from apps.settings_engine.services import get_setting

        min_chars = get_setting("search-min-query-chars")
        if not isinstance(min_chars, int) or min_chars < 1:
            min_chars = 2
        limit = get_setting("search-result-limit")
        if not isinstance(limit, int) or limit < 1:
            limit = 20

        query = str(request.query_params.get("q", "")).strip()
        if len(query) < min_chars:
            return Response({"query": query, "courses": [], "lessons": []})

        courses = Course.objects.filter(
            models.Q(title__icontains=query) | models.Q(description__icontains=query),
            is_published=True,
        ).select_related("instructor")[:limit]

        lessons = Lesson.objects.filter(
            title__icontains=query,
            is_published=True,
            course__is_published=True,
        ).select_related("course")[:limit]

        return Response(
            {
                "query": query,
                "courses": [
                    {
                        "slug": c.slug,
                        "title": c.title,
                        "instructor": c.instructor.display_name or "",
                    }
                    for c in courses
                ],
                "lessons": [
                    {
                        "id": l.id,
                        "title": l.title,
                        "course_slug": l.course.slug,
                        "course_title": l.course.title,
                    }
                    for l in lessons
                ],
            }
        )


class AdminStatsView(APIView):
    """Headline numbers for the admin console dashboard."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from apps.accounts.models import Subscription
        from apps.engagement.models import PointsEvent
        from apps.tutor.models import TutorSession

        UserModel = get_user_model()
        today = timezone.localdate()
        now = timezone.now()

        return Response(
            {
                "users_total": UserModel.objects.count(),
                "premium_users": Subscription.objects.filter(
                    is_active=True, expires_at__gt=now
                ).count(),
                "courses_total": Course.objects.count(),
                "courses_published": Course.objects.filter(is_published=True).count(),
                "enrollments_total": Enrollment.objects.count(),
                "quiz_attempts_today": QuizAttempt.objects.filter(
                    completed_at__date=today
                ).count(),
                "tutor_sessions_today": TutorSession.objects.filter(
                    created_at__date=today
                ).count(),
                "points_awarded_today": PointsEvent.objects.filter(
                    created_at__date=today
                ).count(),
            }
        )
