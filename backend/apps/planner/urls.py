from django.urls import path

from .views import ToggleItemView, WeekPlanView, GlobalPlannerRebuildView

urlpatterns = [
    path("week/", WeekPlanView.as_view(), name="planner-week"),
    path("rebuild/", GlobalPlannerRebuildView.as_view(), name="planner-rebuild"),
    path("items/<int:item_id>/toggle/", ToggleItemView.as_view(), name="planner-toggle"),
]
