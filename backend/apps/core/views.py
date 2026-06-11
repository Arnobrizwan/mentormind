from django.conf import settings
from django.core.cache import cache
from django.db import connections, models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ml_client, services
from .models import (
    Course,
    Enrollment,
    Lesson,
    ProctoringLog,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    ShortAnswerQuestion,
    ShortAnswerSubmission,
)
from .permissions import IsEnrolledStudentOrInstructor, IsInstructor, is_instructor
from .serializers import (
    CourseSerializer,
    EnrollmentSerializer,
    LessonSerializer,
    ProctoringLogSerializer,
    QuizSerializer,
    QuizAttemptSerializer,
    QuizQuestionSerializer,
    ShortAnswerQuestionSerializer,
    ShortAnswerSubmissionSerializer,
)

MAX_PROCTOR_IMAGE_BYTES = 8 * 1024 * 1024
# Consecutive flagged frames before the instructor is alerted — edge-triggered
# so one long violation produces one notification, not one per frame.
PROCTOR_ALERT_STREAK = 3


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
    def readiness(self, request, slug=None):
        """Exam-readiness per enrolled student — weakest first. Only for
        this course's instructor/staff."""
        course = self.get_object()
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only this course's instructor can view readiness."},
                status=status.HTTP_403_FORBIDDEN,
            )
        from . import readiness as readiness_module

        return Response(readiness_module.course_readiness(course))

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
        queryset = Lesson.objects.select_related("course")

        # Staff see everything
        if user.is_staff or user.is_superuser:
            return queryset

        # Published lessons of published courses the user is enrolled in
        enrolled = models.Q(
            is_published=True,
            course__is_published=True,
            course__enrollments__student=user,
        )
        # Instructors additionally manage their own courses' lessons (drafts included)
        if is_instructor(user):
            return queryset.filter(models.Q(course__instructor=user) | enrolled).distinct()
        return queryset.filter(enrolled).distinct()

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
        if self.action in ["list", "retrieve", "submit", "proctor_frame"]:
            return [IsAuthenticated(), IsEnrolledStudentOrInstructor()]
        return [IsInstructor()]

    def get_queryset(self):
        user = self.request.user
        # Explicit ordering: Quiz has no Meta.ordering and paginated lists
        # need a stable one
        queryset = (
            Quiz.objects.select_related("course")
            .prefetch_related("questions")
            .order_by("id")
        )

        # Staff see everything
        if user.is_staff or user.is_superuser:
            return queryset

        # Quizzes of published courses the user is enrolled in
        enrolled = models.Q(
            course__is_published=True, course__enrollments__student=user
        )
        # Instructors additionally manage their own courses' quizzes
        if is_instructor(user):
            return queryset.filter(models.Q(course__instructor=user) | enrolled).distinct()
        return queryset.filter(enrolled).distinct()

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

        # Attempt cap — a SiteSetting so operators tune it live (dynamic-first)
        from apps.settings_engine.services import get_setting

        max_attempts = get_setting("quiz_max_attempts")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            max_attempts = 3
        attempts_so_far = (
            QuizAttempt.objects.using("default")
            .filter(enrollment=enrollment, quiz=quiz)
            .count()
        )
        if attempts_so_far >= max_attempts:
            return Response(
                {"error": f"Attempt limit reached ({max_attempts} per quiz)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submitted_answers = request.data.get("answers", {})
        if not isinstance(submitted_answers, dict):
            return Response(
                {"error": "answers must be an object mapping question id to option index."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        correct_answers = 0
        answers_detail = {}
        for q in questions:
            ans = submitted_answers.get(str(q.id), submitted_answers.get(q.id))
            correct = False
            selected = None
            try:
                # Non-numeric answers count as wrong, not as a server error
                if ans is not None:
                    selected = int(ans)
                    correct = selected == q.correct_option_index
            except (TypeError, ValueError):
                selected = None
            if correct:
                correct_answers += 1
            answers_detail[str(q.id)] = {
                "selected": selected,
                "correct": correct,
                "topic": q.topic,
            }

        score = round((correct_answers / total_questions) * 100, 2)

        attempt = QuizAttempt.objects.using("default").create(
            enrollment=enrollment,
            quiz=quiz,
            score=score,
            total_questions=total_questions,
            correct_answers=correct_answers,
            answers=answers_detail,
        )

        serializer = QuizAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path="generate-draft",
        permission_classes=[IsInstructor],
    )
    def generate_draft(self, request):
        """Draft MCQs from a lesson with the ml-service generator. Returns
        suggestions only — the instructor reviews/edits and saves through
        the normal quiz/question endpoints, so AI output is never published
        unreviewed."""
        lesson_id = request.data.get("lesson")
        try:
            lesson = (
                Lesson.objects.using("default")
                .select_related("course")
                .get(id=lesson_id)
            )
        except (Lesson.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "lesson is required and must exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if lesson.course.instructor != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only this course's instructor can generate quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not lesson.content.strip():
            return Response(
                {"error": "This lesson has no content to generate from."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Generous timeout: generation may run the in-process LLM
            result = ml_client.post_json(
                "/v1/generate/quiz",
                {
                    "content": lesson.content[:16000],
                    "topic": lesson.title,
                    "count": 5,
                },
                timeout=90,
            )
        except ml_client.MLServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        questions = result.get("questions") or []
        return Response(
            {
                "lesson": lesson.id,
                "course": lesson.course_id,
                "suggested_title": f"{lesson.title} — checkpoint quiz",
                "questions": questions,
                "engine": result.get("engine", "heuristic"),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="proctor-frame",
        permission_classes=[IsAuthenticated],
    )
    def proctor_frame(self, request, pk=None):
        """Check one webcam snapshot during a quiz. The frame goes to the
        ml-service face detector; only the verdict is stored — never the
        image. After PROCTOR_ALERT_STREAK consecutive flagged frames the
        course instructor gets one notification."""
        quiz = self.get_object()
        enrollment = (
            Enrollment.objects.using("default")
            .filter(student=request.user, course=quiz.course)
            .first()
        )
        if not enrollment:
            return Response(
                {"error": "You must be enrolled in the course to be proctored."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image = request.FILES.get("image")
        if image is None or not (image.content_type or "").startswith("image/"):
            return Response(
                {"error": "An image file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw = image.read()
        if len(raw) > MAX_PROCTOR_IMAGE_BYTES:
            return Response(
                {"error": "Image too large (8 MB max)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = ml_client.post_image(
                "/v1/proctor/check",
                raw,
                filename=image.name or "frame.jpg",
                content_type=image.content_type,
            )
        except ml_client.MLServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        verdict = result.get("verdict")
        if verdict not in ProctoringLog.Verdict.values:
            return Response(
                {"error": "Proctoring service returned an unknown verdict."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        log = ProctoringLog.objects.using("default").create(
            enrollment=enrollment,
            quiz=quiz,
            faces=int(result.get("faces", 0)),
            verdict=verdict,
        )

        recent = list(
            ProctoringLog.objects.using("default")
            .filter(enrollment=enrollment, quiz=quiz)
            .order_by("-created_at")[: PROCTOR_ALERT_STREAK + 1]
        )
        streak_now = len(recent) >= PROCTOR_ALERT_STREAK and all(
            entry.is_violation for entry in recent[:PROCTOR_ALERT_STREAK]
        )
        # Edge trigger: the frame before the streak was clean (or absent).
        streak_is_new = len(recent) == PROCTOR_ALERT_STREAK or (
            len(recent) > PROCTOR_ALERT_STREAK
            and not recent[PROCTOR_ALERT_STREAK].is_violation
        )
        if streak_now and streak_is_new:
            from apps.notifications.models import Notification
            from apps.notifications.services import notify

            student = request.user.display_name or request.user.email
            notify(
                quiz.course.instructor,
                Notification.Kind.PROCTORING,
                title=f"Proctoring alert: {student}",
                body=(
                    f"{PROCTOR_ALERT_STREAK} consecutive flagged webcam frames "
                    f"({log.get_verdict_display().lower()}) during '{quiz.title}'."
                ),
                link=f"/courses/{quiz.course.slug}",
            )

        return Response(
            {"verdict": verdict, "faces": log.faces},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], permission_classes=[IsInstructor])
    def proctoring(self, request, pk=None):
        """Exam-integrity timeline — every student's frame verdicts for this
        quiz, grouped per student. Instructor/staff only."""
        quiz = self.get_object()
        if quiz.course.instructor != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only this course's instructor can view proctoring logs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        logs = (
            ProctoringLog.objects.using("default")
            .filter(quiz=quiz)
            .select_related("enrollment__student")
            .order_by("enrollment_id", "created_at")
        )
        sessions = {}
        for log in logs:
            student = log.enrollment.student
            entry = sessions.setdefault(
                log.enrollment_id,
                {
                    "enrollment": log.enrollment_id,
                    "student_email": student.email,
                    "student_name": student.display_name,
                    "violations": 0,
                    "logs": [],
                },
            )
            entry["logs"].append(ProctoringLogSerializer(log).data)
            if log.is_violation:
                entry["violations"] += 1
        return Response(list(sessions.values()))


class ShortAnswerQuestionViewSet(viewsets.ModelViewSet):
    """Free-text questions with ml-service rubric grading. Instructors
    author them (mark scheme included); enrolled students see only the
    prompt and submit answers for instant criteria-by-criteria feedback."""

    serializer_class = ShortAnswerQuestionSerializer
    filterset_fields = ["course", "lesson"]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "submit", "submissions"]:
            return [IsAuthenticated()]
        return [IsInstructor()]

    def get_queryset(self):
        user = self.request.user
        queryset = ShortAnswerQuestion.objects.using("default").select_related("course")
        if user.is_staff or user.is_superuser:
            return queryset
        enrolled = models.Q(
            is_published=True,
            course__is_published=True,
            course__enrollments__student=user,
        )
        if is_instructor(user):
            return queryset.filter(
                models.Q(course__instructor=user) | enrolled
            ).distinct()
        return queryset.filter(enrolled).distinct()

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if course.instructor != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You are not the instructor of this course.")
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit(self, request, pk=None):
        """Grade the student's free-text answer against the mark scheme."""
        question = self.get_object()
        enrollment = (
            Enrollment.objects.using("default")
            .filter(student=request.user, course=question.course)
            .first()
        )
        if not enrollment:
            return Response(
                {"error": "You must be enrolled in the course to submit an answer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_text = str(request.data.get("answer", "")).strip()[:8000]
        if not answer_text:
            return Response(
                {"error": "answer is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Attempt cap — same live-tunable pattern as quizzes
        from apps.settings_engine.services import get_setting

        max_attempts = get_setting("short_answer_max_attempts")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            max_attempts = 3
        attempts_so_far = (
            ShortAnswerSubmission.objects.using("default")
            .filter(question=question, enrollment=enrollment)
            .count()
        )
        if attempts_so_far >= max_attempts:
            return Response(
                {"error": f"Attempt limit reached ({max_attempts} per question)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Generous timeout: grading may run the in-process LLM
            result = ml_client.post_json(
                "/v1/grade/short-answer",
                {
                    "question": question.prompt,
                    "student_answer": answer_text,
                    "mark_scheme": question.mark_scheme,
                    "max_score": question.max_score,
                },
                timeout=60,
            )
        except ml_client.MLServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        try:
            score = max(0, min(int(result.get("score", 0)), question.max_score))
        except (TypeError, ValueError):
            score = 0
        engine = result.get("engine")
        if engine not in ShortAnswerSubmission.Engine.values:
            engine = ShortAnswerSubmission.Engine.HEURISTIC

        submission = ShortAnswerSubmission.objects.using("default").create(
            question=question,
            enrollment=enrollment,
            answer_text=answer_text,
            score=score,
            max_score=question.max_score,
            criteria_met=[str(c) for c in result.get("criteria_met") or []],
            criteria_missing=[str(c) for c in result.get("criteria_missing") or []],
            feedback=str(result.get("feedback", "")),
            engine=engine,
        )
        return Response(
            ShortAnswerSubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def submissions(self, request, pk=None):
        """A student sees their own attempts; the course instructor sees all."""
        question = self.get_object()
        queryset = (
            ShortAnswerSubmission.objects.using("default")
            .filter(question=question)
            .select_related("enrollment__student")
        )
        user = request.user
        if not (user.is_staff or user.is_superuser or question.course.instructor == user):
            queryset = queryset.filter(enrollment__student=user)
        return Response(
            ShortAnswerSubmissionSerializer(queryset, many=True).data
        )


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

                headers = {}
                if getattr(settings, "ML_API_KEY", ""):
                    headers["X-API-Key"] = settings.ML_API_KEY
                req = urllib.request.Request(
                    f"{ml_url.rstrip('/')}/healthz", headers=headers
                )
                with urllib.request.urlopen(req, timeout=2) as res:
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


class PracticeRecommendationsView(APIView):
    """Weak-topic practice feed: the student's per-topic accuracy plus the
    questions they should attempt next, weakest topic first."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from . import adaptive

        return Response(adaptive.recommendations(request.user))


class StudentReadinessView(APIView):
    """The student's own exam-readiness score per enrolled course."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from . import readiness as readiness_module

        return Response(readiness_module.student_readiness(request.user))


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
