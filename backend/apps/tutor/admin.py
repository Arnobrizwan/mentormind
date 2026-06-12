from django.contrib import admin

from .models import TutorMessage, TutorSession


class TutorMessageInline(admin.TabularInline):
    model = TutorMessage
    extra = 0
    readonly_fields = ("role", "content", "feedback", "created_at")


@admin.register(TutorSession)
class TutorSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "subject", "level", "title", "updated_at")
    search_fields = ("user__email", "title")
    inlines = [TutorMessageInline]


from .models import TutorMessage  # noqa: E402


@admin.register(TutorMessage)
class TutorMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "feedback", "created_at")
    list_filter = ("role", "feedback")
    search_fields = ("content", "session__user__email")
    readonly_fields = ("created_at",)
