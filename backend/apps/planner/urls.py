from django.urls import path

from .views import (
    GlobalPlannerRebuildView,
    ToggleItemView,
    WeekPlanIcsView,
    WeekPlanView,
)

urlpatterns = [
    path("week/", WeekPlanView.as_view(), name="planner-week"),
    path("week.ics", WeekPlanIcsView.as_view(), name="planner-week-ics"),
    path("rebuild/", GlobalPlannerRebuildView.as_view(), name="planner-rebuild"),
    path("items/<int:item_id>/toggle/", ToggleItemView.as_view(), name="planner-toggle"),
]
