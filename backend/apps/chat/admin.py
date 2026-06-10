from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("course", "sender", "body", "created_at")
    list_filter = ("course",)
    search_fields = ("body", "sender__email")
