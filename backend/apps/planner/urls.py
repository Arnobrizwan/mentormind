from django.urls import path

from .views import ToggleItemView, WeekPlanView

urlpatterns = [
    path("week/", WeekPlanView.as_view(), name="planner-week"),
    path("items/<int:item_id>/toggle/", ToggleItemView.as_view(), name="planner-toggle"),
]
