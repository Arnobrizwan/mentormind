from django.urls import path

from .views import (
    DailyLoginView,
    MyEngagementView,
    PointsHistoryView,
    WeeklyLeaderboardView,
)

urlpatterns = [
    path("me/", MyEngagementView.as_view(), name="engagement-me"),
    path("daily-login/", DailyLoginView.as_view(), name="engagement-daily-login"),
    path("leaderboard/", WeeklyLeaderboardView.as_view(), name="engagement-leaderboard"),
    path("history/", PointsHistoryView.as_view(), name="engagement-history"),
]
