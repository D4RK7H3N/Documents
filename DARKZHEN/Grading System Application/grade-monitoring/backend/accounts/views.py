from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from audit.services import record_audit
from common.permissions import IsAdmin, IsAuthenticatedActive

from .models import User
from .serializers import (
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    UserSerializer,
    absolute_file_url,
)
from .services import invalidate_user_refresh_tokens


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticatedActive]

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            from rest_framework_simplejwt.tokens import RefreshToken

            try:
                token = RefreshToken(refresh)
                token.blacklist()
            except Exception:
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticatedActive]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        serializer.save()
        invalidate_user_refresh_tokens(user)
        record_audit(actor=user, action="auth.change_password", entity="user", entity_id=user.id)
        return Response({"detail": "Password changed."})


class MeView(APIView):
    permission_classes = [IsAuthenticatedActive]

    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)


class MeAvatarView(APIView):
    permission_classes = [IsAuthenticatedActive]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        old_path = user.avatar.name if user.avatar else None
        if user.avatar:
            user.avatar.delete(save=False)
        user.avatar = serializer.validated_data["avatar"]
        with transaction.atomic():
            user.save(update_fields=["avatar"])
            record_audit(
                actor=user,
                action="profile.avatar",
                entity="user",
                entity_id=user.id,
                old_values={"avatar": old_path},
                new_values={"avatar": user.avatar.name},
            )
        return Response({"avatar_url": absolute_file_url(request, user.avatar)})

    def delete(self, request):
        user = request.user
        if user.avatar:
            old_path = user.avatar.name
            user.avatar.delete(save=False)
            user.avatar = ""
            with transaction.atomic():
                user.save(update_fields=["avatar"])
                record_audit(
                    actor=user,
                    action="profile.avatar",
                    entity="user",
                    entity_id=user.id,
                    old_values={"avatar": old_path},
                    new_values={"avatar": None},
                )
        return Response({"avatar_url": None})


class CreateStaffView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        role = request.data.get("role") or "teacher"
        last_name = (request.data.get("last_name") or "").strip()
        first_name = (request.data.get("first_name") or "").strip()
        if len(username) < 3:
            return Response(
                {"error": {"code": "validation_error", "message": "Username must be at least 3 characters."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not last_name or not first_name:
            return Response(
                {"error": {"code": "validation_error", "message": "Last name and first name are required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if role not in ("teacher", "admin"):
            return Response(
                {"error": {"code": "validation_error", "message": "Role must be teacher or admin."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"error": {"code": "conflict", "message": "Username already exists."}},
                status=status.HTTP_409_CONFLICT,
            )
        user = User.objects.create_user(
            username=username,
            role=role,
            last_name=last_name,
            first_name=first_name,
        )
        temporary_password = user.set_temporary_password()
        record_audit(
            actor=request.user,
            action="user.create",
            entity="user",
            entity_id=user.id,
            new_values={"username": username, "role": role, "name": user.display_name},
        )
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "role": role,
                "temporary_password": temporary_password,
            },
            status=status.HTTP_201_CREATED,
        )


class SetPasswordView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        from django.contrib.auth.password_validation import validate_password
        from rest_framework.exceptions import ValidationError as DRFValidationError

        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response(
                {"error": {"code": "not_found", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        password = request.data.get("password") or ""
        try:
            validate_password(password, user=user)
        except DRFValidationError as exc:
            raise exc
        user.set_password(password)
        user.must_change_password = False
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["password", "must_change_password", "failed_login_attempts", "locked_until"])
        invalidate_user_refresh_tokens(user)
        record_audit(
            actor=request.user,
            action="user.set_password",
            entity="user",
            entity_id=user.id,
            new_values={"username": user.username},
        )
        return Response({"detail": f"Password set for {user.display_name}."})


class ResetPasswordView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response(
                {"error": {"code": "not_found", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        temporary_password = user.set_temporary_password()
        invalidate_user_refresh_tokens(user)
        record_audit(
            actor=request.user,
            action="user.reset_password",
            entity="user",
            entity_id=user.id,
            new_values={"username": user.username},
        )
        return Response({"temporary_password": temporary_password})


class UserStatusView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response(
                {"error": {"code": "not_found", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        is_active = bool(request.data.get("is_active"))
        if user.id == request.user.id and not is_active:
            return Response(
                {"error": {"code": "conflict", "message": "You cannot deactivate your own account."}},
                status=status.HTTP_409_CONFLICT,
            )
        user.is_active = is_active
        user.save(update_fields=["is_active"])
        if not is_active:
            invalidate_user_refresh_tokens(user)
        record_audit(
            actor=request.user,
            action="user.status",
            entity="user",
            entity_id=user.id,
            old_values={"is_active": not is_active},
            new_values={"is_active": is_active},
        )
        return Response({"id": user.id, "is_active": user.is_active})
