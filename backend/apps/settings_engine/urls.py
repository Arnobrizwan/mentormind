from django.urls import path

from .views import PublicSettingsView

urlpatterns = [
    path("public/", PublicSettingsView.as_view(), name="public-settings"),
]
