from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityCalendarView,
    BadgeViewSet,
    DailyLoginView,
    GuardianLinkView,
    GuardianSummaryView,
    MyEngagementView,
    PointsHistoryView,
    RemediationTicketViewSet,
    WeeklyLeaderboardView,
)

router = DefaultRouter()
router.register("badges/manage", BadgeViewSet, basename="badge-manage")
router.register("risk/tickets", RemediationTicketViewSet, basename="remediation-ticket")

urlpatterns = [
    path("me/", MyEngagementView.as_view(), name="engagement-me"),
    path("daily-login/", DailyLoginView.as_view(), name="engagement-daily-login"),
    path("leaderboard/", WeeklyLeaderboardView.as_view(), name="engagement-leaderboard"),
    path("history/", PointsHistoryView.as_view(), name="engagement-history"),
    path("activity/", ActivityCalendarView.as_view(), name="engagement-activity"),
    path("guardian/link/", GuardianLinkView.as_view(), name="guardian-link"),
    path(
        "guardian/summary/<str:token>/",
        GuardianSummaryView.as_view(),
        name="guardian-summary",
    ),
    path("", include(router.urls)),
]
