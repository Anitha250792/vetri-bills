from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import DeviceToken
from .serializers import (
    DeviceTokenSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]  # partial updates only

    def get_object(self):
        return self.request.user


class DeviceTokenView(APIView):
    """Save the Expo push token after login (used for expiry / low-stock pushes)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeviceTokenSerializer

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DeviceToken.objects.update_or_create(
            token=serializer.validated_data["token"],
            defaults={"user": request.user, "platform": serializer.validated_data.get("platform", "")},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
