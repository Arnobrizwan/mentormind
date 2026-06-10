from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PublicSettingsView, SiteSettingViewSet

router = DefaultRouter()
router.register("manage", SiteSettingViewSet, basename="setting-manage")

urlpatterns = [
    path("public/", PublicSettingsView.as_view(), name="public-settings"),
    path("", include(router.urls)),
]
