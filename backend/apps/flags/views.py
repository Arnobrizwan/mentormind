from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class FlagsView(APIView):
    """All feature flags as {key: bool} — Angular hides/shows modules from this."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(services.all_flags())
