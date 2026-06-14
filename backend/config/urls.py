from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_media
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
    path("api/v1/revision/", include("apps.revision.urls")),
    path("api/v1/planner/", include("apps.planner.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# Serve user-uploaded media (avatars, course covers) in every environment.
# django.conf.urls.static.static() is a no-op when DEBUG=False, so production
# would 404 on /media/* — Caddy already routes /media/* here, and on this
# single-VPS demo (local FileSystemStorage) Django must serve it. For heavier
# deployments, front this with object storage (R2_*) or a Caddy file_server.
urlpatterns += [
    re_path(
        r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"),
        serve_media,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
