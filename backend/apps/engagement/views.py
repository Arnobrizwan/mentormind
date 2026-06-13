from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsInstructor, IsCronOrInstructor

from . import services
from .models import Badge, GuardianLink, PointsEvent, RemediationTicket
from .serializers import BadgeSerializer, RemediationTicketSerializer


class MyEngagementView(APIView):
    """Everything the dashboard gamification strip needs in one call."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        recent = [
            {"action": e.action, "points": e.points, "at": e.created_at}
            for e in PointsEvent.objects.using("default").filter(user=user)[:10]
        ]
        return Response(
            {
                "points_total": services.total_points(user),
                "streak": services.current_streak(user),
                "daily_login_claimed": services.daily_login_claimed(user),
                "daily_login_points": services.point_value("daily_login"),
                "badges": services.badge_progress(user),
                "recent_events": recent,
            }
        )


class DailyLoginView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        claimed, points = services.claim_daily_login(request.user)
        return Response(
            {
                "claimed": claimed,
                "points": points,
                "points_total": services.total_points(request.user),
            }
        )


class WeeklyLeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(services.weekly_leaderboard())


class BadgeViewSet(viewsets.ModelViewSet):
    """Staff CRUD for badge definitions — rules and thresholds are DB
    rows, so the admin console tunes gamification live."""

    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = [IsAdminUser]


class PointsHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        paginator = PageNumberPagination()
        events = PointsEvent.objects.using("default").filter(user=request.user)
        page = paginator.paginate_queryset(events, request)
        data = [
            {"action": e.action, "points": e.points, "at": e.created_at} for e in page
        ]
        return paginator.get_paginated_response(data)


class ActivityCalendarView(APIView):
    """The student's active days (last ~17 weeks) + current streak — feeds
    the profile heatmap."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import timedelta

        from django.utils import timezone

        from .models import DailyActivity

        since = timezone.localdate() - timedelta(days=119)
        days = list(
            DailyActivity.objects.using("default")
            .filter(user=request.user, date__gte=since)
            .order_by("date")
            .values_list("date", flat=True)
        )
        return Response(
            {
                "since": since,
                "days": days,
                "streak": services.current_streak(request.user),
            }
        )


class RemediationTicketViewSet(viewsets.ModelViewSet):
    """The Student Success queue — tickets opened by the weekly dropout-risk
    scan. Instructors triage them (open → contacted → resolved) and can
    trigger an on-demand scan."""

    serializer_class = RemediationTicketSerializer
    permission_classes = [IsCronOrInstructor]
    http_method_names = ["get", "patch", "post"]
    filterset_fields = ["status", "risk"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from apps.flags.services import flag_enabled
        from rest_framework.exceptions import PermissionDenied
        if not flag_enabled("dropout_risk", default=True):
            raise PermissionDenied("Dropout risk prediction is currently disabled.")

    def get_queryset(self):
        queryset = RemediationTicket.objects.using("default").select_related("student")
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return queryset
        # Instructors only see (and triage) students from their own courses —
        # the same isolation as rosters, readiness and proctoring timelines.
        return queryset.filter(
            student__enrollments__course__instructor=user
        ).distinct()

    def create(self, request, *args, **kwargs):
        # Tickets are opened by the risk scan, never by hand.
        return Response(
            {"detail": "Tickets are created by the dropout-risk scan."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["post"])
    def scan(self, request):
        """Run the dropout-risk sweep now instead of waiting for Monday.
        Single-flight: the platform-wide sweep hits the ml-service once per
        student, so concurrent or repeated triggers are refused."""
        from django.core.cache import cache
        from django.conf import settings

        cron_key = request.headers.get("X-Cron-Key")
        is_cron = cron_key and getattr(settings, "ML_API_KEY", "") and cron_key == settings.ML_API_KEY

        if not cache.add("engagement:dropout-scan-lock", 1, timeout=600):
            return Response(
                {"queued": False, "detail": "A scan is already in progress."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            if is_cron:
                # Run synchronously to support free Render environments without Celery workers
                from .risk import scan_students
                scanned, flagged = scan_students()
                cache.delete("engagement:dropout-scan-lock")
                return Response({
                    "queued": False,
                    "detail": f"scanned {scanned} student(s), flagged {flagged} high-risk"
                }, status=status.HTTP_200_OK)
            else:
                from .tasks import scan_dropout_risk
                result = scan_dropout_risk.delay()
                return Response(
                    {"queued": True, "task_id": result.id},
                    status=status.HTTP_202_ACCEPTED,
                )
        except Exception as e:
            cache.delete("engagement:dropout-scan-lock")
            raise e


class GuardianLinkView(APIView):
    """The student's own guardian share-link: GET to inspect, POST to
    create (idempotent), DELETE to revoke. Revoking deletes the row, so
    the public summary URL dies immediately."""

    permission_classes = [IsAuthenticated]

    def _payload(self, link):
        return {
            "token": link.token,
            "created_at": link.created_at,
            "path": f"/guardian/{link.token}",
        }

    def get(self, request):
        link = GuardianLink.objects.using("default").filter(student=request.user).first()
        return Response({"link": self._payload(link) if link else None})

    def post(self, request):
        link, created = GuardianLink.objects.using("default").get_or_create(
            student=request.user
        )
        return Response(
            {"link": self._payload(link)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        GuardianLink.objects.using("default").filter(student=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GuardianSummaryView(APIView):
    """The parent-facing weekly digest, readable with only the share token —
    no account, no login. Deliberately PII-light: display name, progress and
    readiness, never the student's email or anything another student wrote."""

    permission_classes = [AllowAny]

    def get(self, request, token):
        from datetime import timedelta

        from django.db.models import Sum
        from django.utils import timezone

        from apps.core.adaptive import weak_topics
        from apps.core.models import QuizAttempt
        from apps.core.readiness import student_readiness

        link = (
            GuardianLink.objects.using("default")
            .filter(token=token)
            .select_related("student")
            .first()
        )
        if link is None:
            return Response(
                {"detail": "This link is no longer active."},
                status=status.HTTP_404_NOT_FOUND,
            )
        student = link.student
        since = timezone.now() - timedelta(days=7)

        points_week = (
            PointsEvent.objects.using("default")
            .filter(user=student, created_at__gte=since)
            .aggregate(total=Sum("points"))["total"]
            or 0
        )

        recent_quizzes = [
            {
                "quiz": attempt.quiz.title,
                "course": attempt.quiz.course.title,
                "score": attempt.score,
                "completed_at": attempt.completed_at,
            }
            for attempt in (
                QuizAttempt.objects.using("default")
                .filter(enrollment__student=student)
                .select_related("quiz__course")
                .order_by("-completed_at")[:5]
            )
        ]

        courses = [
            {
                "course_title": entry["course_title"],
                "readiness": entry["readiness"],
                "predicted_grade": entry["predicted_grade"],
                "components": entry["components"],
            }
            for entry in student_readiness(student)
        ]

        return Response(
            {
                "student_name": student.display_name or "Student",
                "generated_at": timezone.now(),
                "points_week": points_week,
                "streak": services.current_streak(student),
                "weak_topics": weak_topics(student)[:3],
                "courses": courses,
                "recent_quizzes": recent_quizzes,
            }
        )
