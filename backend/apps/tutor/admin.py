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
