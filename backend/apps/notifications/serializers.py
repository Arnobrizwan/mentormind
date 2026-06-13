from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "kind", "title", "body", "link", "is_read", "created_at")
        read_only_fields = fields


class PushSubscriptionSerializer(serializers.Serializer):
    """Validates the browser's PushSubscription.toJSON() shape:
    {endpoint, keys: {p256dh, auth}}."""

    endpoint = serializers.URLField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField(), write_only=True)

    def validate(self, attrs):
        keys = attrs.get("keys") or {}
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")
        if not p256dh or not auth:
            raise serializers.ValidationError("keys.p256dh and keys.auth are required.")
        attrs["p256dh"] = p256dh
        attrs["auth"] = auth
        return attrs
