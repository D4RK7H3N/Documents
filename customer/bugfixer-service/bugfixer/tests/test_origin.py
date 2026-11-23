from django.test import TestCase
from django.urls import reverse

from bugfixer.models import Project


class OriginCheckTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Shop",
            repo_url="https://github.com/acme/shop.git",
            allowed_origins=["https://good.example"],
        )
        self.url = reverse("report-create")

    def _post(self, origin, key=None):
        return self.client.post(
            self.url,
            {"message": "The button is broken."},
            HTTP_X_PROJECT_KEY=key or self.project.public_key,
            HTTP_ORIGIN=origin,
        )

    def test_allowed_origin_creates_report(self):
        response = self._post("https://good.example")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "queued")

    def test_disallowed_origin_rejected(self):
        self.assertEqual(self._post("https://evil.example").status_code, 403)

    def test_missing_origin_rejected(self):
        response = self.client.post(
            self.url, {"message": "broken"}, HTTP_X_PROJECT_KEY=self.project.public_key
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_key_rejected(self):
        self.assertEqual(self._post("https://good.example", key="wrong").status_code, 401)

    def test_cors_reflects_only_allowed_origin(self):
        allowed = self.client.options(self.url, HTTP_ORIGIN="https://good.example")
        self.assertEqual(allowed["Access-Control-Allow-Origin"], "https://good.example")
        denied = self.client.options(self.url, HTTP_ORIGIN="https://evil.example")
        self.assertNotIn("Access-Control-Allow-Origin", denied)

    def test_status_endpoint_never_leaks_private_fields(self):
        created = self._post("https://good.example").json()
        url = reverse("report-status", args=[created["id"]])
        response = self.client.get(url, {"token": created["status_token"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"status", "message"})
        for field in ("result_log", "branch", "pr_url", "console_log", "status_token"):
            self.assertNotIn(field, response.json())
        bad = self.client.get(url, {"token": "not-the-token"})
        self.assertEqual(bad.status_code, 404)
