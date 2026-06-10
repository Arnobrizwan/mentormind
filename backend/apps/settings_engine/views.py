from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import SiteSetting
from .serializers import SiteSettingSerializer


class PublicSettingsView(APIView):
    """All public settings as one dict — the Angular apps bootstrap from this."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(services.get_public_settings())


class SiteSettingViewSet(viewsets.ModelViewSet):
    """Staff-only settings management for the admin console. Cache
    invalidation rides the model's save/delete signals."""

    queryset = SiteSetting.objects.using("default").all()
    serializer_class = SiteSettingSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None
