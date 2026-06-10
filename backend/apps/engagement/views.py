from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import PointsEvent


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
