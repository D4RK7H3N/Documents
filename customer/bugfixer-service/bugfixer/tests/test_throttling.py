from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from bugfixer.models import Project


def rates(ip, key):
    config = dict(settings.REST_FRAMEWORK)
    config["DEFAULT_THROTTLE_RATES"] = {"report_ip": ip, "report_key": key}
    return config


@override_settings(REST_FRAMEWORK=rates("2/min", "100/min"))
class IPThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.project = Project.objects.create(
            name="Shop",
            repo_url="https://github.com/acme/shop.git",
            allowed_origins=["https://good.example"],
        )
        self.url = reverse("report-create")

    def _post(self):
        return self.client.post(
            self.url,
            {"message": "broken"},
            HTTP_X_PROJECT_KEY=self.project.public_key,
            HTTP_ORIGIN="https://good.example",
        )

    def test_third_request_from_same_ip_is_throttled(self):
        self.assertEqual(self._post().status_code, 201)
        self.assertEqual(self._post().status_code, 201)
        self.assertEqual(self._post().status_code, 429)


@override_settings(REST_FRAMEWORK=rates("100/min", "2/min"))
class KeyThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.project = Project.objects.create(
            name="Shop",
            repo_url="https://github.com/acme/shop.git",
            allowed_origins=["https://good.example"],
        )
        self.url = reverse("report-create")

    def _post(self, key):
        return self.client.post(
            self.url,
            {"message": "broken"},
            HTTP_X_PROJECT_KEY=key,
            HTTP_ORIGIN="https://good.example",
        )

    def test_third_request_with_same_key_is_throttled(self):
        self.assertEqual(self._post(self.project.public_key).status_code, 201)
        self.assertEqual(self._post(self.project.public_key).status_code, 201)
        self.assertEqual(self._post(self.project.public_key).status_code, 429)
