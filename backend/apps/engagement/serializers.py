from rest_framework import serializers

from .models import Badge, RemediationTicket


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


class RemediationTicketSerializer(serializers.ModelSerializer):
    student_email = serializers.ReadOnlyField(source="student.email")
    student_name = serializers.ReadOnlyField(source="student.display_name")

    class Meta:
        model = RemediationTicket
        fields = [
            "id",
            "student",
            "student_email",
            "student_name",
            "risk",
            "probability",
            "features",
            "status",
            "note",
            "created_at",
            "updated_at",
        ]
        # Tickets are machine-opened; instructors only move status and notes.
        read_only_fields = [
            "id",
            "student",
            "risk",
            "probability",
            "features",
            "created_at",
            "updated_at",
        ]
