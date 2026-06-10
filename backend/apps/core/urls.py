from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminStatsView,
    CourseViewSet,
    EnrollmentViewSet,
    HealthView,
    LessonViewSet,
    QuizQuestionViewSet,
    QuizViewSet,
    SearchView,
    SystemStatusView,
)

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")
router.register("lessons", LessonViewSet, basename="lesson")
router.register("quizzes", QuizViewSet, basename="quiz")
router.register("questions", QuizQuestionViewSet, basename="question")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("system/", SystemStatusView.as_view(), name="system-status"),
    path("search/", SearchView.as_view(), name="search"),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("", include(router.urls)),
]
