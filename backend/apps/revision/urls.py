from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FlashcardViewSet,
    GenerateFlashcardsView,
    RevisionExportView,
    RevisionQueueView,
    ReviewView,
)

router = DefaultRouter()
router.register("flashcards", FlashcardViewSet, basename="flashcard")

urlpatterns = [
    path("queue/", RevisionQueueView.as_view(), name="revision-queue"),
    path("review/", ReviewView.as_view(), name="revision-review"),
    path("export.csv", RevisionExportView.as_view(), name="revision-export"),
    path("generate/", GenerateFlashcardsView.as_view(), name="revision-generate"),
    path("", include(router.urls)),
]
