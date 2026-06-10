from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FeatureFlagViewSet, FlagsView

router = DefaultRouter()
router.register("manage", FeatureFlagViewSet, basename="flag-manage")

urlpatterns = [
    path("", FlagsView.as_view(), name="flags"),
    path("", include(router.urls)),
]
