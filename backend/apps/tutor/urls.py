from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import TutorFeedbackReviewView, TutorSessionViewSet

router = DefaultRouter()
router.register("sessions", TutorSessionViewSet, basename="tutor-session")

urlpatterns = [
    path("feedback/", TutorFeedbackReviewView.as_view(), name="tutor-feedback-review"),
    *router.urls,
]
