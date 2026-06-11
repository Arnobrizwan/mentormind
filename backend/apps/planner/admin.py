from django.contrib import admin

from .models import StudyPlan


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "week_start", "completion_pct", "generated_at")
    list_filter = ("week_start",)
