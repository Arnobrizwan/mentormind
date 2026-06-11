from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsInstructor

from . import services
from .models import Badge, PointsEvent, RemediationTicket
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


class RemediationTicketViewSet(viewsets.ModelViewSet):
    """The Student Success queue — tickets opened by the weekly dropout-risk
    scan. Instructors triage them (open → contacted → resolved) and can
    trigger an on-demand scan."""

    serializer_class = RemediationTicketSerializer
    permission_classes = [IsInstructor]
    http_method_names = ["get", "patch", "post"]
    filterset_fields = ["status", "risk"]

    def get_queryset(self):
        return (
            RemediationTicket.objects.using("default")
            .select_related("student")
            .all()
        )

    def create(self, request, *args, **kwargs):
        # Tickets are opened by the risk scan, never by hand.
        return Response(
            {"detail": "Tickets are created by the dropout-risk scan."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["post"])
    def scan(self, request):
        """Run the dropout-risk sweep now instead of waiting for Monday."""
        from .tasks import scan_dropout_risk

        result = scan_dropout_risk.delay()
        return Response(
            {"queued": True, "task_id": result.id},
            status=status.HTTP_202_ACCEPTED,
        )
