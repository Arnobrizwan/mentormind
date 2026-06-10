from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings_engine.services import get_setting

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()

DEFAULT_AVATAR_MB = 5


def max_avatar_mb() -> int:
    configured = get_setting("avatar-max-mb")
    return configured if isinstance(configured, int) and configured > 0 else DEFAULT_AVATAR_MB


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class AvatarUploadView(APIView):
    """Multipart avatar upload — stored on the default storage backend
    (local disk in dev, Cloudflare R2 / any S3-compatible bucket when the
    R2_* environment variables are set)."""

    parser_classes = [MultiPartParser]

    def put(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "Upload a file under the 'file' multipart key."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit_mb = max_avatar_mb()
        if file.size > limit_mb * 1024 * 1024:
            return Response(
                {"error": f"Avatar must be {limit_mb} MB or smaller."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (file.content_type or "").startswith("image/"):
            return Response(
                {"error": "Avatar must be an image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        user.avatar.save(file.name, file, save=False)
        user.avatar_url = user.avatar.url
        user.save(update_fields=["avatar", "avatar_url"])
        return Response(UserSerializer(user, context={"request": request}).data)


class SubscribeView(APIView):
    """Simulated premium checkout — instantly activates the plan.
    Plan durations come from settings rows (premium-monthly-days /
    premium-yearly-days) with 30/365 defaults."""

    def post(self, request):
        from datetime import timedelta

        from django.utils import timezone

        from apps.settings_engine.services import get_setting

        from .models import Subscription

        plan = request.data.get("plan")
        if plan not in (Subscription.Plan.MONTHLY, Subscription.Plan.YEARLY):
            return Response(
                {"error": "plan must be 'monthly' or 'yearly'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        default_days = 30 if plan == Subscription.Plan.MONTHLY else 365
        days = get_setting(f"premium-{plan}-days")
        if not isinstance(days, int):
            days = default_days

        Subscription.objects.update_or_create(
            user=request.user,
            defaults={
                "plan": plan,
                "is_active": True,
                "expires_at": timezone.now() + timedelta(days=days),
            },
        )
        request.user.refresh_from_db()
        return Response(UserSerializer(request.user, context={"request": request}).data)
