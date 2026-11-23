import io
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from audit.models import AuditLog

from .base import auth, login, make_section, make_student, make_user


def png_upload(name="photo.png", size=(64, 64)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (38, 60, 82)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class ProfileDetailsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_user("admin", "adminpass123", "admin")
        res = login(self.client, "admin", "adminpass123")
        auth(self.client, res.data["access"])

    def test_me_includes_profile_fields(self):
        res = self.client.get("/api/v1/me/")
        self.assertEqual(res.status_code, 200)
        for field in ("email", "phone", "first_name", "last_name", "avatar_url"):
            self.assertIn(field, res.data)
        self.assertIsNone(res.data["avatar_url"])

    def test_staff_patch_updates_details_and_writes_audit(self):
        res = self.client.patch(
            "/api/v1/me/",
            {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com", "phone": "09171234567"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["first_name"], "Ada")
        self.assertEqual(res.data["display_name"], "Lovelace, Ada")
        self.assertEqual(res.data["phone"], "09171234567")
        entry = AuditLog.objects.filter(action="profile.update", entity_id=self.admin.id).latest("timestamp")
        self.assertIn("first_name", entry.old_values)
        self.assertEqual(entry.new_values["first_name"], "Ada")
        self.assertEqual(entry.new_values["phone"], "09171234567")

    def test_patch_rejects_invalid_email(self):
        res = self.client.patch("/api/v1/me/", {"email": "not-an-email"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_student_can_edit_contact_but_not_name(self):
        section = make_section()
        profile, password = make_student("123456789020", "Sample Student", section, self.admin)
        res = login(self.client, profile.lrn, password)
        auth(self.client, res.data["access"])

        ok = self.client.patch("/api/v1/me/", {"email": "student@example.com", "phone": "0999"}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data["email"], "student@example.com")
        self.assertEqual(ok.data["display_name"], "Sample Student")

        blocked = self.client.patch("/api/v1/me/", {"first_name": "Hacked"}, format="json")
        self.assertEqual(blocked.status_code, 400)
        profile.user.refresh_from_db()
        self.assertEqual(profile.full_name, "Sample Student")

    def test_patch_rolls_back_when_audit_write_fails(self):
        self.admin.refresh_from_db()
        self.client.raise_request_exception = False
        with mock.patch("accounts.serializers.record_audit", side_effect=RuntimeError("db connection lost")):
            res = self.client.patch("/api/v1/me/", {"first_name": "Changed"}, format="json")
        self.assertEqual(res.status_code, 500)
        self.admin.refresh_from_db()
        self.assertNotEqual(self.admin.first_name, "Changed")


class AvatarTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user("teacher1", "teacherpass123", "teacher")
        res = login(self.client, "teacher1", "teacherpass123")
        auth(self.client, res.data["access"])

    def test_upload_replace_and_remove_avatar(self):
        first = self.client.post("/api/v1/me/avatar/", {"avatar": png_upload()}, format="multipart")
        self.assertEqual(first.status_code, 200)
        first_url = first.data["avatar_url"]
        self.assertIn("/media/avatars/", first_url)
        self.user.refresh_from_db()
        first_path = self.user.avatar.path
        self.assertTrue(AuditLog.objects.filter(action="profile.avatar").exists())

        second = self.client.post("/api/v1/me/avatar/", {"avatar": png_upload()}, format="multipart")
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(second.data["avatar_url"], first_url)
        import os
        self.assertFalse(os.path.exists(first_path))

        removed = self.client.delete("/api/v1/me/avatar/")
        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.data["avatar_url"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)

    def test_avatar_rejects_non_image_content(self):
        bad = SimpleUploadedFile("fake.png", b"this is not an image", content_type="image/png")
        res = self.client.post("/api/v1/me/avatar/", {"avatar": bad}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_avatar_rejects_oversize_file(self):
        big = SimpleUploadedFile("big.png", b"0" * (2 * 1024 * 1024 + 1), content_type="image/png")
        res = self.client.post("/api/v1/me/avatar/", {"avatar": big}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_avatar_requires_file(self):
        res = self.client.post("/api/v1/me/avatar/", {}, format="multipart")
        self.assertEqual(res.status_code, 400)
