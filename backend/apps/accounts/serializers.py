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
            # Set only by the avatar upload endpoint — not client-writable
            "avatar_url",
            "roles",
            "is_staff",
            "is_premium",
            "subscription",
            "date_joined",
        )

    is_premium = serializers.BooleanField(read_only=True)
    subscription = serializers.SerializerMethodField()

    def get_subscription(self, obj):
        subscription = getattr(obj, "subscription", None)
        if not subscription:
            return None
        return {
            "plan": subscription.plan,
            "is_active": subscription.is_active,
            "expires_at": subscription.expires_at,
        }
