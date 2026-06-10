from rest_framework import serializers

from .models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ("id", "sender_name", "body", "created_at")
        read_only_fields = fields

    def get_sender_name(self, obj):
        return obj.sender.display_name or obj.sender.email
