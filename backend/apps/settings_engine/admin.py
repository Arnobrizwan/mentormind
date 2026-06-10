from django.contrib import admin

from .models import SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "is_public", "description", "updated_at")
    list_filter = ("is_public",)
    search_fields = ("key", "description")
