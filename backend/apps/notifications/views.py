from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import webpush
from .models import Notification, PushSubscription
from .serializers import NotificationSerializer, PushSubscriptionSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """The signed-in user's notifications, newest first."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Own notifications must be read-your-own-writes consistent
        return Notification.objects.using("default").filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread": count})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"marked_read": updated}, status=status.HTTP_200_OK)


class PushConfigView(APIView):
    """The VAPID public key the browser needs to subscribe. `enabled` is
    false when the server has no keys, so the SPA can hide the opt-in."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        enabled = webpush.is_configured()
        subscribed = (
            PushSubscription.objects.filter(user=request.user).exists()
            if enabled
            else False
        )
        return Response(
            {
                "enabled": enabled,
                "public_key": webpush.public_key() if enabled else "",
                "subscribed": subscribed,
            }
        )


class PushSubscribeView(APIView):
    """Register (idempotent) or remove this browser's push subscription."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not webpush.is_configured():
            return Response(
                {"detail": "Push notifications are not enabled on this server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Re-subscribing from the same browser updates the keys + owner rather
        # than duplicating (endpoint is unique).
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"],
            defaults={
                "user": request.user,
                "p256dh": data["p256dh"],
                "auth": data["auth"],
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
        )
        return Response({"subscribed": True}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        # Require the specific endpoint: an empty value must never fan out to
        # "delete all of this user's subscriptions" — that would silently kill
        # reminders on their other devices. Dead rows that no client can name
        # are pruned on the next send (404/410). Pass ?all=true to opt into a
        # full wipe (e.g. account-level "disable everywhere").
        endpoint = str(request.data.get("endpoint", "")).strip()
        wipe_all = str(request.data.get("all", "")).lower() in ("1", "true")
        qs = PushSubscription.objects.filter(user=request.user)
        if endpoint:
            qs = qs.filter(endpoint=endpoint)
        elif not wipe_all:
            return Response(
                {"detail": "endpoint is required (or pass all=true to remove every device)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
