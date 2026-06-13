from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .pastpapers_views import (
    PaperQuestionDetailView,
    PaperQuestionsView,
    PaperSampleView,
    PaperSubjectsView,
)
from .views import (
    AdminStatsView,
    CourseViewSet,
    EnrollmentViewSet,
    HealthView,
    LessonViewSet,
    OmrGradeView,
    PracticeOcrView,
    PracticeRecommendationsView,
    QuizQuestionViewSet,
    QuizViewSet,
    SearchView,
    ShortAnswerQuestionViewSet,
    StudentReadinessView,
    SystemStatusView,
)

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")
router.register("lessons", LessonViewSet, basename="lesson")
router.register("quizzes", QuizViewSet, basename="quiz")
router.register("questions", QuizQuestionViewSet, basename="question")
router.register("short-answers", ShortAnswerQuestionViewSet, basename="short-answer")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("system/", SystemStatusView.as_view(), name="system-status"),
    path("search/", SearchView.as_view(), name="search"),
    path(
        "practice/recommendations/",
        PracticeRecommendationsView.as_view(),
        name="practice-recommendations",
    ),
    path(
        "practice/readiness/",
        StudentReadinessView.as_view(),
        name="practice-readiness",
    ),
    path("practice/ocr/", PracticeOcrView.as_view(), name="practice-ocr"),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("pastpapers/subjects/", PaperSubjectsView.as_view(), name="paper-subjects"),
    path("pastpapers/questions/", PaperQuestionsView.as_view(), name="paper-questions"),
    path("pastpapers/questions/<str:question_id>/", PaperQuestionDetailView.as_view(), name="paper-question-detail"),
    path("pastpapers/sample/", PaperSampleView.as_view(), name="paper-sample"),
    path("omr/grade/", OmrGradeView.as_view(), name="omr-grade"),
    path("", include(router.urls)),
]
