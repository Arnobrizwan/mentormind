from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password", "display_name")
        read_only_fields = ("id",)

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SlugRelatedField(
        source="groups", many=True, read_only=True, slug_field="name"
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "avatar",
            "avatar_url",
            "roles",
            "is_staff",
            "is_premium",
            "subscription",
            "date_joined",
        )
        read_only_fields = (
            "id",
            "email",
            "avatar",
            "roles",
            "is_staff",
            "is_premium",
            "subscription",
            "date_joined",
        )

    is_premium = serializers.BooleanField(read_only=True)
    subscription = serializers.SerializerMethodField()
    # Computed (not the raw DB column) so it's always a working, absolute URL —
    # this also repairs rows saved before MEDIA_URL gained its leading slash.
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        if getattr(obj, "avatar", None):
            url = obj.avatar.url
        elif obj.avatar_url:
            url = obj.avatar_url
        else:
            return ""
        # Normalize a legacy relative media path (no leading slash) so the
        # browser doesn't resolve it against the current SPA route.
        if not url.startswith(("http://", "https://", "/")):
            url = "/" + url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request is not None else url

    def get_subscription(self, obj):
        subscription = getattr(obj, "subscription", None)
        if not subscription:
            return None
        return {
            "plan": subscription.plan,
            "is_active": subscription.is_active,
            "expires_at": subscription.expires_at,
        }
