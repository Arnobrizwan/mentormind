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
        fields = ("id", "email", "display_name", "avatar_url", "roles", "date_joined")
        read_only_fields = ("id", "email", "roles", "date_joined")
