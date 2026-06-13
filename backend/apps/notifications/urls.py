from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, PushConfigView, PushSubscribeView

router = DefaultRouter()
router.register("", NotificationViewSet, basename="notification")

# Push routes are listed before the catch-all router so they resolve first.
urlpatterns = [
    path("push/config/", PushConfigView.as_view(), name="push-config"),
    path("push/subscribe/", PushSubscribeView.as_view(), name="push-subscribe"),
    *router.urls,
]
