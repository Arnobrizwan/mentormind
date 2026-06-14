from django.urls import path

from .views import (
    GlobalPlannerRebuildView,
    StudyInsightView,
    ToggleItemView,
    WeekPlanIcsView,
    WeekPlanView,
)

urlpatterns = [
    path("week/", WeekPlanView.as_view(), name="planner-week"),
    path("week.ics", WeekPlanIcsView.as_view(), name="planner-week-ics"),
    path("insight/", StudyInsightView.as_view(), name="planner-insight"),
    path("rebuild/", GlobalPlannerRebuildView.as_view(), name="planner-rebuild"),
    path("items/<int:item_id>/toggle/", ToggleItemView.as_view(), name="planner-toggle"),
]
