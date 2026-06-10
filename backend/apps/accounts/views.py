from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()

MAX_AVATAR_BYTES = 5 * 1024 * 1024


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
        if file.size > MAX_AVATAR_BYTES:
            return Response(
                {"error": "Avatar must be 5 MB or smaller."},
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
