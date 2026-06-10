from rest_framework import serializers

from .models import Badge


class BadgeSerializer(serializers.ModelSerializer):
    rule_choices = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Badge
        fields = [
            "id",
            "key",
            "name",
            "description",
            "icon",
            "rule",
            "threshold",
            "order",
            "rule_choices",
        ]
        read_only_fields = ["id"]

    def get_rule_choices(self, _obj):
        return [{"value": value, "label": label} for value, label in Badge.Rule.choices]
