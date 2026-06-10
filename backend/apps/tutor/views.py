from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement.services import award_points
from apps.flags.services import flag_enabled

from . import services
from .models import TutorMessage, TutorSession
from .serializers import (
    TutorMessageSerializer,
    TutorSessionListSerializer,
    TutorSessionSerializer,
)


class TutorSessionViewSet(viewsets.ModelViewSet):
    """The student's AI tutor sessions — create, resume, chat, delete."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_serializer_class(self):
        return TutorSessionListSerializer if self.action == "list" else TutorSessionSerializer

    def get_queryset(self):
        return (
            TutorSession.objects.using("default")
            .filter(user=self.request.user)
            .prefetch_related("messages")
        )

    def create(self, request, *args, **kwargs):
        if not flag_enabled("ai_tutor", default=True):
            return Response(
                {"detail": "The AI tutor is currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def quota(self, request):
        """Daily message allowance — null limit means unlimited (premium)."""
        limit = services.daily_limit(request.user)
        return Response(
            {
                "limit": limit,
                "used": services.messages_used_today(request.user),
                "remaining": services.remaining_today(request.user),
                "is_premium": getattr(request.user, "is_premium", False),
            }
        )

    @action(detail=True, methods=["post"])
    def messages(self, request, pk=None):
        """Send a question; the tutor's reply comes back in the same response."""
        if not flag_enabled("ai_tutor", default=True):
            return Response(
                {"detail": "The AI tutor is currently disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        session = self.get_object()
        content = str(request.data.get("content", "")).strip()[:4000]
        if not content:
            return Response(
                {"error": "content is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        remaining = services.remaining_today(request.user)
        if remaining is not None and remaining <= 0:
            return Response(
                {
                    "error": "Daily message limit reached.",
                    "limit": services.daily_limit(request.user),
                    "upgrade": "Go premium for unlimited tutoring.",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user_message = TutorMessage.objects.create(
            session=session, role=TutorMessage.Role.USER, content=content
        )
        if not session.title:
            session.title = content[:80]
        session.save(update_fields=["title", "updated_at"])

        try:
            reply_text = services.generate_reply(session)
        except services.TutorError as exc:
            user_message.delete()  # don't burn quota on provider failures
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        assistant_message = TutorMessage.objects.create(
            session=session, role=TutorMessage.Role.ASSISTANT, content=reply_text
        )
        award_points(request.user, "tutor_question")

        return Response(
            {
                "user_message": TutorMessageSerializer(user_message).data,
                "assistant_message": TutorMessageSerializer(assistant_message).data,
                "remaining": services.remaining_today(request.user),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="messages/(?P<message_id>[0-9]+)/feedback")
    def feedback(self, request, pk=None, message_id=None):
        """Thumbs up (+1) / down (-1) on an assistant reply."""
        session = self.get_object()
        value = request.data.get("value")
        if value not in (1, -1):
            return Response(
                {"error": "value must be 1 or -1."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            message = session.messages.get(
                id=message_id, role=TutorMessage.Role.ASSISTANT
            )
        except TutorMessage.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        message.feedback = value
        message.save(update_fields=["feedback"])
        return Response(TutorMessageSerializer(message).data)
