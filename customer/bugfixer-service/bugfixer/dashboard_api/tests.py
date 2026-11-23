from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ..models import BugReport, Project, Status


class DashboardPermissionTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Shop", repo_url="https://github.com/acme/shop.git")
        self.report = BugReport.objects.create(project=self.project, message="broken")
        self.urls = [
            reverse("dashboard-projects"),
            reverse("dashboard-reports"),
            reverse("dashboard-stats"),
            reverse("dashboard-settings"),
        ]

    def test_anonymous_is_forbidden(self):
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_non_staff_is_forbidden(self):
        user = User.objects.create_user("viewer", password="pass1234")
        self.client.force_login(user)
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_can_access(self):
        user = User.objects.create_user("admin", password="pass1234", is_staff=True)
        self.client.force_login(user)
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_csrf_endpoint_returns_token(self):
        response = self.client.get(reverse("dashboard-csrf"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("csrfToken"))

    def test_settings_returns_only_booleans(self):
        user = User.objects.create_user("admin", password="pass1234", is_staff=True)
        self.client.force_login(user)
        data = self.client.get(reverse("dashboard-settings")).json()
        self.assertTrue(all(isinstance(v, bool) for v in data.values()))


class DashboardActionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("admin", password="pass1234", is_staff=True)
        self.client.force_login(self.user)
        self.project = Project.objects.create(name="Shop", repo_url="https://github.com/acme/shop.git")
        self.report = BugReport.objects.create(
            project=self.project,
            message="broken",
            status=Status.FAILED,
            result_log="previous failure",
            branch="fix/report-old",
            pr_url="https://github.com/acme/shop/pull/1",
        )

    def test_requeue_clears_worker_fields(self):
        response = self.client.post(reverse("dashboard-requeue", args=[self.report.pk]))
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Status.QUEUED)
        self.assertEqual(self.report.result_log, "")
        self.assertEqual(self.report.branch, "")
        self.assertEqual(self.report.pr_url, "")

    def test_reject_sets_status(self):
        response = self.client.post(reverse("dashboard-reject", args=[self.report.pk]))
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Status.REJECTED)

    def test_approve_pr_uses_shared_action(self):
        self.project.auto_pr = False
        self.project.save(update_fields=["auto_pr"])
        self.report.status = Status.FIX_READY
        self.report.branch = "fix/report-1"
        self.report.pr_url = ""
        self.report.save()
        with patch("bugfixer.services.report_actions.create_pull_request", return_value="https://github.com/acme/shop/pull/2"):
            response = self.client.post(reverse("dashboard-approve-pr", args=[self.report.pk]))
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.pr_url, "https://github.com/acme/shop/pull/2")
