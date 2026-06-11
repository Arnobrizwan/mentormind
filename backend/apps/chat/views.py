from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Course
from apps.flags.services import flag_enabled

from .models import ChatMessage
from .permissions import can_join_chat
from .serializers import ChatMessageSerializer


class CourseChatHistoryView(APIView):
    """Last 50 messages of a course chat — for hydrating the room on join."""

    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        # Absent flag means enabled — consistent with the other features
        if not flag_enabled("chat", default=True):
            return Response(
                {"detail": "Chat is currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            course = Course.objects.get(slug=slug)
        except Course.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not can_join_chat(request.user, course):
            return Response(
                {"detail": "Enroll in the course to join its chat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        messages = list(
            ChatMessage.objects.using("default")
            .filter(course=course)
            .select_related("sender")
            .order_by("-created_at")[:50]
        )[::-1]
        return Response(ChatMessageSerializer(messages, many=True).data)
