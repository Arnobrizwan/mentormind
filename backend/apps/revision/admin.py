from django.contrib import admin

from .models import Flashcard, ReviewCard


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "topic", "front", "source", "is_published")
    list_filter = ("is_published", "source", "course")
    search_fields = ("front", "back", "topic")


@admin.register(ReviewCard)
class ReviewCardAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "flashcard", "due_at", "repetitions", "ease_factor")
    list_filter = ("user",)
