from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class PublicSettingsView(APIView):
    """All public settings as one dict — the Angular apps bootstrap from this."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(services.get_public_settings())
