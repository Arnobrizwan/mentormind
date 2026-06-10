from rest_framework import serializers

from .models import TutorMessage, TutorSession


class TutorMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorMessage
        fields = ("id", "role", "content", "feedback", "created_at")
        read_only_fields = ("id", "role", "content", "created_at")


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
