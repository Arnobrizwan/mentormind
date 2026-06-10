from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import FeatureFlag
from .serializers import FeatureFlagSerializer


class FlagsView(APIView):
    """All feature flags as {key: bool} — Angular hides/shows modules from this."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(services.all_flags())


class FeatureFlagViewSet(viewsets.ModelViewSet):
    """Staff-only flag management — the admin console flips modules live here."""

    queryset = FeatureFlag.objects.using("default").all()
    serializer_class = FeatureFlagSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None
