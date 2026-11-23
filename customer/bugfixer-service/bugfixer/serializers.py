from PIL import Image
from django.conf import settings
from rest_framework import serializers

from .models import BugReport
from .services.guards import redact

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}


def validate_image_size(value, max_bytes=None):
    """Reject uploads larger than the configured limit. Exposed for tests."""
    max_bytes = max_bytes or settings.MAX_UPLOAD_BYTES
    if value is not None and getattr(value, "size", 0) > max_bytes:
        raise serializers.ValidationError("Screenshot must be 5 MB or smaller.")
    return value


class ReportCreateSerializer(serializers.ModelSerializer):
    message = serializers.CharField(max_length=2000, min_length=1, required=True)
    screenshot = serializers.ImageField(required=False, allow_null=True)
    reporter_id = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    reporter_email = serializers.EmailField(required=False, allow_blank=True, default="")
    page_url = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    user_agent = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    console_log = serializers.CharField(max_length=8000, required=False, allow_blank=True, default="")

    class Meta:
        model = BugReport
        fields = [
            "message",
            "screenshot",
            "page_url",
            "user_agent",
            "console_log",
            "reporter_id",
            "reporter_email",
        ]

    def validate_screenshot(self, value):
        validate_image_size(value)
        if value is None:
            return value
        content_type = getattr(value, "content_type", "")
        if content_type and content_type not in ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError("Only PNG, JPG and WEBP screenshots are allowed.")
        try:
            value.seek(0)
            image_format = Image.open(value).format
            value.seek(0)
        except Exception:
            raise serializers.ValidationError("Invalid image file.")
        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise serializers.ValidationError("Only PNG, JPG and WEBP screenshots are allowed.")
        return value

    def validate_console_log(self, value):
        return redact(value)


class ReportStatusSerializer(serializers.ModelSerializer):
    message = serializers.CharField(source="friendly_message", read_only=True)

    class Meta:
        model = BugReport
        fields = ["status", "message"]
