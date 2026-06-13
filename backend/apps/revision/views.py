import csv

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Enrollment, Lesson
from apps.core.permissions import IsInstructor

from . import sm2
from .models import Flashcard, ReviewCard
from .serializers import FlashcardSerializer, QueueCardSerializer

QUEUE_SIZE = 20


class FlashcardViewSet(viewsets.ModelViewSet):
    """Instructor CRUD for flashcards — including reviewing/publishing the
    AI-generated drafts. Students never hit this; they study through the
    queue endpoints."""

    serializer_class = FlashcardSerializer
    permission_classes = [IsInstructor]
    filterset_fields = ["course", "lesson", "is_published", "source"]

    def get_queryset(self):
        queryset = Flashcard.objects.using("default").select_related("course")
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return queryset
        return queryset.filter(course__instructor=user)

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if course.instructor != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You are not the instructor of this course.")
        serializer.save(source=Flashcard.Source.INSTRUCTOR)


class GenerateFlashcardsView(APIView):
    """Instructor kicks off AI flashcard generation for a lesson. The
    Celery task calls the ml-service and files the results as unpublished
    drafts; a notification lands when they're ready to review."""

    permission_classes = [IsInstructor]

    def post(self, request):
        lesson_id = request.data.get("lesson")
        try:
            lesson = Lesson.objects.using("default").select_related("course").get(
                id=lesson_id
            )
        except (Lesson.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "lesson is required and must exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if lesson.course.instructor != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only this course's instructor can generate flashcards."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not lesson.content.strip():
            return Response(
                {"error": "This lesson has no content to generate from."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import generate_flashcards_for_lesson

        result = generate_flashcards_for_lesson.delay(lesson.id, request.user.id)
        return Response(
            {"queued": True, "task_id": result.id},
            status=status.HTTP_202_ACCEPTED,
        )


class RevisionQueueView(APIView):
    """The student's due cards. New published cards from enrolled courses
    are pulled into the schedule lazily, due immediately."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        course_ids = list(
            Enrollment.objects.using("default")
            .filter(student=user)
            .values_list("course_id", flat=True)
        )

        # Adopt any published cards the student hasn't scheduled yet.
        unseen = (
            Flashcard.objects.using("default")
            .filter(course_id__in=course_ids, is_published=True)
            .exclude(review_cards__user=user)
        )
        ReviewCard.objects.using("default").bulk_create(
            [ReviewCard(user=user, flashcard=card, due_at=now) for card in unseen],
            ignore_conflicts=True,
        )

        due = (
            ReviewCard.objects.using("default")
            .filter(
                user=user,
                due_at__lte=now,
                flashcard__is_published=True,
                flashcard__course_id__in=course_ids,
            )
            .select_related("flashcard__course")
            .order_by("due_at")
        )
        total_due = due.count()
        return Response(
            {
                "due_count": total_due,
                "cards": QueueCardSerializer(due[:QUEUE_SIZE], many=True).data,
            }
        )


class RevisionExportView(APIView):
    """Export the student's whole deck as a CSV that Anki imports directly.

    Anki reads the leading `#` directives, maps the first two columns to the
    Front/Back of a Basic note, and applies column 3 as tags — so a student
    can take their MentorMind cards offline into Anki with one click. (Plain
    CSV, so Excel / Google Sheets open it too.)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        course_ids = list(
            Enrollment.objects.using("default")
            .filter(student=user)
            .values_list("course_id", flat=True)
        )
        cards = (
            Flashcard.objects.using("default")
            .filter(course_id__in=course_ids, is_published=True)
            .select_related("course")
            .order_by("course_id", "id")
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            'attachment; filename="mentormind-flashcards.csv"'
        )
        # Anki import directives (ignored by spreadsheets).
        response.write("#separator:Comma\n#html:false\n#tags column:3\n")

        writer = csv.writer(response)
        for card in cards:
            tags = " ".join(
                part
                for part in (
                    f"course::{card.course.slug}" if card.course.slug else "",
                    f"topic::{card.topic.replace(' ', '_')}" if card.topic else "",
                )
                if part
            )
            writer.writerow([card.front, card.back, tags])
        return response


class ReviewView(APIView):
    """Grade one card (0-5) and reschedule it with SM-2. Reviewing keeps
    the streak alive and earns points via the engagement ledger."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        card_id = request.data.get("card")
        grade = request.data.get("grade")
        if not isinstance(grade, int) or not 0 <= grade <= 5:
            return Response(
                {"error": "grade must be an integer 0-5."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            card = (
                ReviewCard.objects.using("default")
                .select_related("flashcard")
                .get(id=card_id, user=request.user)
            )
        except (ReviewCard.DoesNotExist, ValueError, TypeError):
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Only due cards can be graded — otherwise re-reviewing the same
        # card in a loop farms unlimited engagement points.
        if card.due_at > timezone.now():
            return Response(
                {"error": "This card is not due yet."},
                status=status.HTTP_409_CONFLICT,
            )

        sm2.review(card, grade)
        card.save()

        from apps.engagement.services import award_points

        award_points(request.user, "revision_review")

        return Response(
            {
                "id": card.id,
                "due_at": card.due_at,
                "interval_days": card.interval_days,
                "repetitions": card.repetitions,
                "ease_factor": round(card.ease_factor, 2),
            }
        )
