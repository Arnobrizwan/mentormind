from rest_framework import serializers

from .models import FeatureFlag


class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = ("id", "key", "enabled", "description", "updated_at")
        read_only_fields = ("id", "updated_at")
