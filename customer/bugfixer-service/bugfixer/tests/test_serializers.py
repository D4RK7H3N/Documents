from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.exceptions import ValidationError

from bugfixer.serializers import ReportCreateSerializer, validate_image_size


def image_bytes(fmt):
    buffer = BytesIO()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(buffer, format=fmt)
    return buffer.getvalue()


class SerializerValidationTests(SimpleTestCase):
    def test_valid_report(self):
        data = {
            "message": "The checkout button does nothing.",
            "screenshot": SimpleUploadedFile("shot.png", image_bytes("PNG"), content_type="image/png"),
        }
        serializer = ReportCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_message_over_2000_chars_rejected(self):
        serializer = ReportCreateSerializer(data={"message": "x" * 2001})
        self.assertFalse(serializer.is_valid())
        self.assertIn("message", serializer.errors)

    def test_non_image_rejected(self):
        data = {
            "message": "broken",
            "screenshot": SimpleUploadedFile("bad.png", b"not really an image", content_type="image/png"),
        }
        serializer = ReportCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("screenshot", serializer.errors)

    def test_disallowed_image_type_rejected(self):
        data = {
            "message": "broken",
            "screenshot": SimpleUploadedFile("animated.gif", image_bytes("GIF"), content_type="image/gif"),
        }
        serializer = ReportCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("screenshot", serializer.errors)

    def test_oversized_upload_rejected(self):
        upload = SimpleUploadedFile(
            "huge.png", b"\x00" * (settings.MAX_UPLOAD_BYTES + 1), content_type="image/png"
        )
        with self.assertRaises(ValidationError):
            validate_image_size(upload)
