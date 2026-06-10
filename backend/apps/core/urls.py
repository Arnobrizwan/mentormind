from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CourseViewSet,
    EnrollmentViewSet,
    HealthView,
    LessonViewSet,
    QuizViewSet,
    SystemStatusView,
)

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")
router.register("lessons", LessonViewSet, basename="lesson")
router.register("quizzes", QuizViewSet, basename="quiz")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("system/", SystemStatusView.as_view(), name="system-status"),
    path("", include(router.urls)),
]
