from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("django_prometheus.urls")),  # /metrics
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/settings/", include("apps.settings_engine.urls")),
    path("api/v1/flags/", include("apps.flags.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
    path("api/v1/engagement/", include("apps.engagement.urls")),
    path("api/v1/tutor/", include("apps.tutor.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
