from rest_framework import serializers

from .models import Flashcard, ReviewCard


class FlashcardSerializer(serializers.ModelSerializer):
    course_title = serializers.ReadOnlyField(source="course.title")

    class Meta:
        model = Flashcard
        fields = (
            "id",
            "course",
            "course_title",
            "lesson",
            "topic",
            "front",
            "back",
            "source",
            "is_published",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "source", "created_at", "updated_at")


class QueueCardSerializer(serializers.ModelSerializer):
    """A due card as the student's revision queue sees it — the client
    flips the card locally, so both sides ship together."""

    front = serializers.ReadOnlyField(source="flashcard.front")
    back = serializers.ReadOnlyField(source="flashcard.back")
    topic = serializers.ReadOnlyField(source="flashcard.topic")
    course_title = serializers.ReadOnlyField(source="flashcard.course.title")

    class Meta:
        model = ReviewCard
        fields = (
            "id",
            "front",
            "back",
            "topic",
            "course_title",
            "interval_days",
            "repetitions",
            "due_at",
        )
        read_only_fields = fields
