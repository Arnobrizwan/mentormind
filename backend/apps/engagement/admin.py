from django.contrib import admin

from .models import AwardedBadge, Badge, PointsEvent


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("icon", "key", "name", "rule", "threshold", "order")
    list_editable = ("threshold", "order")


@admin.register(PointsEvent)
class PointsEventAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "points", "created_at")
    list_filter = ("action",)
    search_fields = ("user__email",)


@admin.register(AwardedBadge)
class AwardedBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "awarded_at")


from .models import DailyActivity, RemediationTicket  # noqa: E402


@admin.register(RemediationTicket)
class RemediationTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "risk", "probability", "status", "created_at")
    list_filter = ("status", "risk")
    search_fields = ("student__email", "note")


@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "date")
    list_filter = ("date",)
    search_fields = ("user__email",)
