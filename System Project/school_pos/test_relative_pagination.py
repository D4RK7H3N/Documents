"""Mission P3 - RelativePagination: `next`/`previous` must never be absolute
backend URLs (sms2-api.darkzhub.asia / gw.darkzhub.asia).

Run: school_pos/.venv/Scripts/python.exe manage.py test -v 2
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from students.models import Student

BAD_HOSTS = ("sms2-api.darkzhub.asia", "gw.darkzhub.asia", "www.darkzhub.asia")


class RelativePaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser(
            username="relpag-admin", password="x", email="relpag@localhost"
        )
        for i in range(1, 4):
            Student.objects.create(
                lrn=f"RELPAG{i:04d}",
                first_name=f"Rel{i}",
                last_name="Pagination",
            )

    def _assert_relative_links(self, body):
        for link in (body.get("next"), body.get("previous")):
            if link is None:
                continue
            self.assertTrue(link.startswith("/"), f"not relative: {link}")
            self.assertNotIn("http://", link)
            for host in BAD_HOSTS:
                self.assertNotIn(host, link)

    def test_page_links_are_relative(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        r = client.get("/api/students/?page_size=2")
        self.assertEqual(r.status_code, 200)
        body = r.data
        self.assertEqual(body["count"], 3)
        self._assert_relative_links(body)
        if body["next"]:
            r2 = client.get(body["next"])
            self.assertEqual(r2.status_code, 200)
            self._assert_relative_links(r2.data)

    def test_response_body_has_no_absolute_backend_urls(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        r = client.get("/api/students/?page_size=2")
        self.assertEqual(r.status_code, 200)
        body_text = json.dumps(r.data)
        for host in BAD_HOSTS:
            self.assertNotIn(host, body_text)
        # `next`/`previous` must be root-relative (or null), per P3.
        for link in (r.data.get("next"), r.data.get("previous")):
            if link is not None:
                self.assertTrue(link.startswith("/"), f"not relative: {link}")
