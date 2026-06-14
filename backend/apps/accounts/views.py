import uuid

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.images import sniff_image_type  # shared magic-byte sniffer
from apps.settings_engine.services import get_setting

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()

DEFAULT_AVATAR_MB = 5


def max_avatar_mb() -> int:
    configured = get_setting("avatar-max-mb")
    return configured if isinstance(configured, int) and configured > 0 else DEFAULT_AVATAR_MB


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login endpoint with its own tight throttle ('auth' scope) — back-
    pressure against credential stuffing and brute force."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


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
        header = file.read(16)
        file.seek(0)
        ext = sniff_image_type(header)
        if ext is None:
            return Response(
                {"error": "Avatar must be a JPEG, PNG, GIF or WebP image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        # Generate our own name — never trust the client filename (path
        # traversal / overwrite). The model's upload_to already prepends
        # "avatars/", so don't repeat it here (that produced avatars/avatars/…).
        safe_name = f"{user.id}-{uuid.uuid4().hex}.{ext}"
        user.avatar.save(safe_name, file, save=False)
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


class PasswordResetView(APIView):
    """Initiates password reset by generating a secure token and sending a mail."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import send_mail
        from django.conf import settings

        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "If the email exists, a reset link has been sent."}, status=status.HTTP_200_OK)

        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        
        origin = request.headers.get("Origin") or "http://localhost:4200"
        reset_link = f"{origin}/auth?mode=reset&uid={uidb64}&token={token}"

        subject = "Reset your MentorMind Password"
        message = (
            f"Hello,\n\n"
            f"You requested a password reset for your MentorMind account.\n"
            f"Please use the following link to reset your password:\n\n"
            f"{reset_link}\n\n"
            f"If you did not request this, please ignore this email.\n"
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception:
            pass

        res_data = {"message": "Password reset link sent."}
        if settings.DEBUG:
            res_data["debug_link"] = reset_link

        return Response(res_data, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """Verifies reset token and sets the new password."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")

        if not all([uidb64, token, password]):
            return Response({"error": "uid, token, and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid link or user does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password, user)
        except ValidationError as e:
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save()
        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
