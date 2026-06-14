import json

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
    def insights(self, request, slug=None):
        """Class-wide topic performance — which topics to teach next.
        Aggregated from per-question quiz detail and graded short answers."""
        course = self.get_object()
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only this course's instructor can view insights."},
                status=status.HTTP_403_FORBIDDEN,
            )
        from collections import defaultdict

        correct = defaultdict(int)
        total = defaultdict(int)
        attempts = QuizAttempt.objects.using("default").filter(quiz__course=course)
        for attempt in attempts:
            for detail in (attempt.answers or {}).values():
                if not isinstance(detail, dict):
                    continue
                topic = (detail.get("topic") or "").strip() or "General"
                total[topic] += 1
                if detail.get("correct"):
                    correct[topic] += 1
        quiz_topics = sorted(
            (
                {
                    "topic": topic,
                    "answers": total[topic],
                    "accuracy": round(100.0 * correct[topic] / total[topic], 1),
                }
                for topic in total
            ),
            key=lambda item: item["accuracy"],
        )

        sa_score = defaultdict(float)
        sa_max = defaultdict(float)
        sa_count = defaultdict(int)
        submissions = (
            ShortAnswerSubmission.objects.using("default")
            .filter(question__course=course)
            .select_related("question")
        )
        for submission in submissions:
            topic = (submission.question.topic or "").strip() or "General"
            sa_count[topic] += 1
            sa_score[topic] += submission.score
            sa_max[topic] += submission.max_score
        short_answer_topics = sorted(
            (
                {
                    "topic": topic,
                    "submissions": sa_count[topic],
                    "avg_pct": round(100.0 * sa_score[topic] / sa_max[topic], 1)
                    if sa_max[topic]
                    else 0.0,
                }
                for topic in sa_count
            ),
            key=lambda item: item["avg_pct"],
        )
        return Response(
            {"quiz_topics": quiz_topics, "short_answer_topics": short_answer_topics}
        )

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

    @action(detail=True, methods=["get"], permission_classes=[IsInstructor])
    def gradebook(self, request, slug=None):
        """The whole class as one CSV — progress, best score per quiz,
        short-answer marks, readiness and predicted grade per student.
        Built for import into Excel/Sheets or an institution's MIS."""
        course = self.get_object()
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only this course's instructor can export the gradebook."},
                status=status.HTTP_403_FORBIDDEN,
            )

        import csv

        from django.http import HttpResponse

        from . import readiness as readiness_module

        quizzes = list(
            Quiz.objects.using("default").filter(course=course).order_by("id")
        )
        sa_questions = list(
            ShortAnswerQuestion.objects.using("default")
            .filter(course=course)
            .order_by("order", "id")
        )
        total_lessons = (
            Lesson.objects.using("default")
            .filter(course=course, is_published=True)
            .count()
        )
        enrollments = (
            Enrollment.objects.using("default")
            .filter(course=course)
            .select_related("student")
            .order_by("student__email")
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="gradebook-{course.slug}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            ["Student", "Email", "Progress %"]
            + [f"Quiz: {quiz.title} (best %)" for quiz in quizzes]
            + ["Short answers (best marks)", "Short answers (max)"]
            + ["Readiness", "Predicted grade"]
        )

        for enrollment in enrollments:
            completed = (
                enrollment.completed_lessons.using("default")
                .filter(is_published=True)
                .count()
            )
            progress = (
                round(100.0 * completed / total_lessons, 1) if total_lessons else 0.0
            )

            best_by_quiz = {}
            for attempt in QuizAttempt.objects.using("default").filter(
                enrollment=enrollment
            ):
                best = best_by_quiz.get(attempt.quiz_id)
                if best is None or attempt.score > best:
                    best_by_quiz[attempt.quiz_id] = attempt.score

            best_by_question = {}
            for submission in ShortAnswerSubmission.objects.using("default").filter(
                enrollment=enrollment
            ):
                best = best_by_question.get(submission.question_id)
                if best is None or submission.score > best:
                    best_by_question[submission.question_id] = submission.score
            sa_earned = sum(
                best_by_question.get(question.id, 0) for question in sa_questions
            )
            sa_max = sum(question.max_score for question in sa_questions)

            scored = readiness_module.enrollment_readiness(
                enrollment, total_lessons=total_lessons
            )
            quiz_cells = [
                ""
                if quiz.id not in best_by_quiz
                else round(best_by_quiz[quiz.id], 1)
                for quiz in quizzes
            ]
            writer.writerow(
                [enrollment.student.display_name, enrollment.student.email, progress]
                + quiz_cells
                + [sa_earned, sa_max, scored["readiness"], scored["predicted_grade"]]
            )

        return response


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

        # One in-flight submit per user+quiz: closes the count-then-create
        # race that let parallel requests beat the attempt cap.
        lock_key = f"quiz-submit-lock:{user.id}:{quiz.id}"
        if not cache.add(lock_key, 1, timeout=15):
            return Response(
                {"error": "Previous submission still processing — try again."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        try:
            return self._graded_submit(request, quiz, user)
        finally:
            cache.delete(lock_key)

    def _graded_submit(self, request, quiz, user):

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
        from apps.flags.services import flag_enabled
        if not flag_enabled("quiz_generation", default=True):
            return Response(
                {"detail": "Quiz generation is currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
        from apps.flags.services import flag_enabled
        if not flag_enabled("proctoring", default=True):
            return Response(
                {"detail": "Exam proctoring is currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
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

    @action(
        detail=True,
        methods=["get"],
        url_path="item-analysis",
        permission_classes=[IsInstructor],
    )
    def item_analysis(self, request, pk=None):
        """Classical item analysis — per-question difficulty, upper-lower
        discrimination, and distractor counts. Flags miskeyed or dead
        questions so the instructor can fix the bank, not just reteach."""
        quiz = self.get_object()
        if quiz.course.instructor != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only this course's instructor can view item analysis."},
                status=status.HTTP_403_FORBIDDEN,
            )
        from . import item_analysis as item_analysis_module

        return Response(item_analysis_module.quiz_item_analysis(quiz))


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
        from apps.flags.services import flag_enabled
        if not flag_enabled("short_answer_grading", default=True):
            return Response(
                {"detail": "Short-answer grading is currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
        question = self.get_object()

        # One in-flight submission per user+question — protects the attempt
        # cap from parallel submits and stops duplicate ml-service grading
        # calls. Generous timeout: grading may run the in-process LLM.
        lock_key = f"sa-submit-lock:{request.user.id}:{question.id}"
        if not cache.add(lock_key, 1, timeout=90):
            return Response(
                {"error": "Previous submission still processing — try again."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        try:
            return self._graded_submit(request, question)
        finally:
            cache.delete(lock_key)

    def _graded_submit(self, request, question):
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
    admin console's system page. Staff-only: infrastructure detail isn't
    for students (and shouldn't be public)."""

    permission_classes = [permissions.IsAdminUser]

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
                # The ml-service is a free-tier cross-cloud Space; a 2s budget
                # flags it as 'error' on a slow-but-alive round-trip. Give it
                # room so the console only shows degraded when it's truly down.
                with urllib.request.urlopen(req, timeout=6) as res:
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


class PracticeOcrView(APIView):
    """OCR a photographed handwritten answer so students can practise on
    paper — the way they'll sit the real exam — and still get instant
    rubric grading. Returns extracted text only; the student reviews and
    corrects it in the answer box before submitting, so OCR mistakes never
    silently cost marks. The image is never stored."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.flags.services import flag_enabled

        if not flag_enabled("handwriting_ocr", default=True):
            return Response(
                {"detail": "Handwriting OCR is currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
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
                "/v1/ocr/extract",
                raw,
                filename=image.name or "answer.jpg",
                content_type=image.content_type,
                timeout=30,
            )
        except ml_client.MLServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"text": str(result.get("text", "")).strip()})


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


class OmrGradeView(APIView):
    """Grade a photographed bubble sheet via the ml-service OMR engine.

    Instructors upload a scan plus a JSON answer key; the ml-service returns
    per-question detections and an overall score. Images are not stored."""
    permission_classes = [IsInstructor]

    def post(self, request):
        from apps.flags.services import flag_enabled

        if not flag_enabled("omr_grading", default=True):
            return Response(
                {"detail": "OMR grading is currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
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

        answer_key_raw = request.data.get("answer_key", "")
        try:
            key = json.loads(answer_key_raw) if isinstance(answer_key_raw, str) else answer_key_raw
            assert isinstance(key, list) and all(isinstance(i, int) for i in key)
            assert key
        except (json.JSONDecodeError, AssertionError, TypeError):
            return Response(
                {"error": "answer_key must be a non-empty JSON array of integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            num_options = int(request.data.get("num_options", 4))
        except (TypeError, ValueError):
            return Response(
                {"error": "num_options must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = ml_client.post_image(
                "/v1/omr/grade",
                raw,
                filename=image.name or "sheet.jpg",
                content_type=image.content_type,
                fields={
                    "answer_key": json.dumps(key),
                    "num_options": str(num_options),
                },
            )
        except ml_client.MLServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(result)


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
