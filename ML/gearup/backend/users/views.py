from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(CreateAPIView):
    """POST /api/auth/register/ - create an account and return JWT tokens."""

    serializer_class = RegisterSerializer
    permission_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/token/ - obtain JWT tokens with username or email."""

    serializer_class = LoginSerializer


class MeView(RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ - current user profile."""

    serializer_class = UserSerializer
    permission_classes = []

    def get_object(self):
        return self.request.user
