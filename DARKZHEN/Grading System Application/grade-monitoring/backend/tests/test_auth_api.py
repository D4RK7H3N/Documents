from django.test import TestCase
from rest_framework.test import APIClient

from .base import auth, login, make_section, make_student, make_user


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_user("admin", "adminpass123", "admin")
        self.section = make_section()

    def test_login_returns_tokens_role_and_flag(self):
        res = login(self.client, "admin", "adminpass123")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["role"], "admin")
        self.assertFalse(res.data["must_change_password"])

    def test_first_login_forces_password_change(self):
        profile, temp_password = make_student(
            "123456789012", "Sample Student", self.section, self.admin, force_ready=False
        )
        res = login(self.client, profile.lrn, temp_password)
        self.assertTrue(res.data["must_change_password"])
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        blocked = self.client.get("/api/v1/me/grades/")
        self.assertEqual(blocked.status_code, 403)

        changed = self.client.post(
            "/api/v1/auth/change-password/",
            {"current_password": temp_password, "new_password": "brand-new-pass-1"},
            format="json",
        )
        self.assertEqual(changed.status_code, 200)

        res2 = login(self.client, profile.lrn, "brand-new-pass-1")
        self.assertFalse(res2.data["must_change_password"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res2.data['access']}")
        allowed = self.client.get("/api/v1/me/grades/")
        self.assertEqual(allowed.status_code, 200)

    def test_lockout_after_five_failed_attempts(self):
        profile, temp_password = make_student("123456789013", "Lockout Student", self.section, self.admin)
        for _ in range(5):
            res = login(self.client, profile.lrn, "wrong-password")
            self.assertEqual(res.status_code, 401)
        locked = login(self.client, profile.lrn, temp_password)
        self.assertEqual(locked.status_code, 400)
        self.assertIn("locked", str(locked.data).lower())
        profile.user.locked_until = None
        profile.user.save()
        ok = login(self.client, profile.lrn, temp_password)
        self.assertEqual(ok.status_code, 200)

    def test_refresh_rotation_and_logout_blacklist(self):
        res = login(self.client, "admin", "adminpass123")
        refresh = res.data["refresh"]
        rotated = self.client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(rotated.status_code, 200)
        self.assertIn("access", rotated.data)
        auth(self.client, res.data["access"])
        logout = self.client.post("/api/v1/auth/logout/", {"refresh": rotated.data["refresh"]}, format="json")
        self.assertEqual(logout.status_code, 204)
        self.client.credentials()
        reuse = self.client.post("/api/v1/auth/refresh/", {"refresh": rotated.data["refresh"]}, format="json")
        self.assertEqual(reuse.status_code, 401)

    def test_student_cannot_access_teacher_and_admin_endpoints(self):
        profile, temp_password = make_student("123456789014", "Limited Student", self.section, self.admin)
        res = login(self.client, profile.lrn, temp_password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        self.assertEqual(self.client.get("/api/v1/teacher/classes/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/admin/students/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/admin/audit-log/").status_code, 403)

    def test_teacher_cannot_access_admin_endpoints(self):
        make_user("teacher1", "teacherpass123", "teacher")
        res = login(self.client, "teacher1", "teacherpass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        self.assertEqual(self.client.get("/api/v1/admin/students/").status_code, 403)

    def test_health_is_public(self):
        res = self.client.get("/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")
