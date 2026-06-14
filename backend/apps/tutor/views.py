from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsInstructor
from apps.engagement.services import award_points
from apps.flags.services import flag_enabled

from . import services
from .models import TutorMessage, TutorSession
from .serializers import (
    TutorFeedbackReviewSerializer,
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

        # Multimodal: a photographed question is "seen" by the ml-service VLM
        # (moondream2, OCR fallback) and joined with whatever the student typed.
        image = request.FILES.get("image")
        if image is not None:
            try:
                extracted = services.describe_image(image, question=content)
            except services.TutorError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if extracted:
                prefix = f"{content}\n\n" if content else ""
                content = f"{prefix}[From my photo]\n{extracted}"[:4000]
            elif not content:
                return Response(
                    {
                        "error": "Couldn't read any text from that photo — "
                        "try a clearer, well-lit shot, or type the question."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not content:
            return Response(
                {"error": "content is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        # cache.add is atomic — one in-flight message per user closes the
        # check-then-create race that let parallel requests beat the quota.
        lock_key = f"tutor-msg-lock:{request.user.id}"
        if not cache.add(lock_key, 1, timeout=10):
            return Response(
                {"error": "Previous message still processing — try again."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        try:
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
        finally:
            # Quota is counted from the persisted message, so the lock only
            # needs to cover check + create — not the slow model call.
            cache.delete(lock_key)
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
        """Thumbs up (+1) / down (-1) on an assistant reply, with an optional
        free-text note when flagging a bad answer (feeds the review surface)."""
        session = self.get_object()
        value = request.data.get("value")
        # `isinstance(True, int)` is True and `True == 1`, so a JSON boolean
        # would otherwise pass `value in (1, -1)` and be stored as a vote.
        if isinstance(value, bool) or value not in (1, -1):
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
        note = str(request.data.get("note", "")).strip()[:500]
        # A note only makes sense on a thumbs-down; a thumbs-up clears any
        # stale flag note left from a previous rating.
        message.feedback_note = note if value == -1 else ""
        message.save(update_fields=["feedback", "feedback_note"])
        return Response(TutorMessageSerializer(message).data)


class TutorFeedbackReviewView(APIView):
    """Instructor/admin review surface for thumbs-down + flagged tutor
    answers — the human-in-the-loop end of the model-improvement flywheel.

    Each row pairs the flagged answer with the question that prompted it and
    a rating summary, so weak or wrong answers can be triaged into better
    training data for the next fine-tune.
    """

    permission_classes = [IsInstructor]

    def get(self, request):
        from django.db.models import Count, Q

        # Force the primary DB: a flag written moments ago must be visible here
        # (the read-replica router would otherwise serve stale data).
        assistant = TutorMessage.objects.using("default").filter(
            role=TutorMessage.Role.ASSISTANT
        )
        agg = assistant.aggregate(
            up=Count("id", filter=Q(feedback=1)),
            down=Count("id", filter=Q(feedback=-1)),
            flagged=Count("id", filter=Q(feedback_note__gt="")),
        )

        flagged = list(
            assistant.filter(feedback=-1)
            .select_related("session", "session__user")
            .order_by("-created_at")[:100]
        )

        # Resolve each flagged answer's prompting question in ONE query instead
        # of one-per-row: pull the candidate user messages for the involved
        # sessions, then pick the latest at-or-before each answer in Python.
        question_map = self._questions_for(flagged)
        return Response(
            {
                "summary": agg,
                "items": TutorFeedbackReviewSerializer(
                    flagged, many=True, context={"questions": question_map}
                ).data,
            }
        )

    @staticmethod
    def _questions_for(answers):
        """{answer_id: prompting_question_text} for a batch of answers."""
        session_ids = {a.session_id for a in answers}
        if not session_ids:
            return {}
        user_msgs = list(
            TutorMessage.objects.using("default")
            .filter(session_id__in=session_ids, role=TutorMessage.Role.USER)
            .order_by("created_at")
            .values("session_id", "content", "created_at")
        )
        by_session = {}
        for msg in user_msgs:
            by_session.setdefault(msg["session_id"], []).append(msg)
        mapping = {}
        for answer in answers:
            prior = [
                m
                for m in by_session.get(answer.session_id, [])
                if m["created_at"] <= answer.created_at
            ]
            mapping[answer.id] = prior[-1]["content"] if prior else ""
        return mapping
