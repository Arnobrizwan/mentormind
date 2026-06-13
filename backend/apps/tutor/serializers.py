from rest_framework import serializers

from .models import TutorMessage, TutorSession


class TutorMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorMessage
        fields = ("id", "role", "content", "feedback", "feedback_note", "created_at")
        read_only_fields = ("id", "role", "content", "created_at")


class TutorFeedbackReviewSerializer(serializers.ModelSerializer):
    """One flagged answer + the question that prompted it, for instructors."""

    question = serializers.SerializerMethodField()
    subject = serializers.CharField(source="session.subject", default="")
    level = serializers.CharField(source="session.level", default="")
    student = serializers.SerializerMethodField()

    class Meta:
        model = TutorMessage
        fields = (
            "id",
            "question",
            "content",
            "feedback",
            "feedback_note",
            "subject",
            "level",
            "student",
            "created_at",
        )

    def get_question(self, obj):
        prior = (
            TutorMessage.objects.filter(
                session=obj.session,
                role=TutorMessage.Role.USER,
                created_at__lte=obj.created_at,
            )
            .order_by("-created_at")
            .first()
        )
        return prior.content if prior else ""

    def get_student(self, obj):
        user = obj.session.user
        # Don't leak the email — a display name or stable pseudonym is enough
        # for an instructor to recognise repeat patterns.
        return getattr(user, "display_name", "") or f"Student #{user.id}"


class TutorSessionSerializer(serializers.ModelSerializer):
    messages = TutorMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = TutorSession
        fields = (
            "id",
            "subject",
            "level",
            "title",
            "messages",
            "last_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "title", "created_at", "updated_at")

    def get_last_message(self, obj):
        last = obj.messages.last()
        return last.content[:120] if last else ""


class TutorSessionListSerializer(TutorSessionSerializer):
    """Without the full message history for the sidebar list."""

    class Meta(TutorSessionSerializer.Meta):
        fields = ("id", "subject", "level", "title", "last_message", "updated_at")
