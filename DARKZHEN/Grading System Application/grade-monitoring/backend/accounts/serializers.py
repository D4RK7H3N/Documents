from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from audit.services import record_audit

from .models import User


def absolute_file_url(request, file):
    if not file:
        return None
    url = file.url
    if not url.startswith("/"):
        url = "/" + url
    return request.build_absolute_uri(url) if request else url


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        user = User.objects.filter(username=attrs.get("username")).first()
        if user and user.is_locked_out:
            raise serializers.ValidationError({"detail": "Account temporarily locked. Try again later."}, code="locked")
        try:
            data = super().validate(attrs)
        except (serializers.ValidationError, AuthenticationFailed):
            if user and user.is_active:
                user.register_failed_login()
            raise
        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account is deactivated."}, code="inactive")
        user.register_successful_login()
        data["role"] = user.role
        data["must_change_password"] = user.must_change_password
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        user = self.context["request"].user
        if user.username and value.lower() == user.username.lower():
            raise serializers.ValidationError("The new password must not equal the username.")
        validate_password(value, user=user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    display_name = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "role", "must_change_password", "name", "display_name",
            "email", "phone", "first_name", "last_name", "avatar_url",
        ]

    def get_name(self, obj):
        return obj.display_name

    def get_avatar_url(self, obj):
        return absolute_file_url(self.context.get("request"), obj.avatar)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone"]

    def validate(self, attrs):
        if self.instance.is_student and ("first_name" in attrs or "last_name" in attrs):
            raise serializers.ValidationError(
                "Student names are managed by the school. Contact your adviser for corrections."
            )
        return attrs

    def update(self, instance, validated_data):
        changed = {
            field: value
            for field, value in validated_data.items()
            if getattr(instance, field) != value
        }
        if changed:
            old = {field: getattr(instance, field) for field in changed}
            with transaction.atomic():
                instance = super().update(instance, validated_data)
                record_audit(
                    actor=instance,
                    action="profile.update",
                    entity="user",
                    entity_id=instance.id,
                    old_values=old,
                    new_values=changed,
                )
        return instance


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.FileField()

    def validate_avatar(self, value):
        allowed = (".png", ".jpg", ".jpeg", ".webp")
        if not value.name.lower().endswith(allowed):
            raise serializers.ValidationError("Photo must be a PNG, JPG or WEBP file.")
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Photo must be smaller than 2 MB.")
        try:
            from PIL import Image

            Image.open(value).verify()
        except Exception:
            raise serializers.ValidationError("The uploaded file is not a valid image.")
        finally:
            value.seek(0)
        return value


class ResetPasswordResultSerializer(serializers.Serializer):
    temporary_password = serializers.CharField()
