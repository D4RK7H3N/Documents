from django.test import SimpleTestCase

from bugfixer.services.guards import find_forbidden, redact


class ForbiddenPathTests(SimpleTestCase):
    def test_builtin_secrets_and_containers(self):
        changed = ["src/app.py", ".env", "Dockerfile", "docker-compose.yml", "src/style.css"]
        self.assertEqual(find_forbidden(changed), [".env", "Dockerfile", "docker-compose.yml"])

    def test_ci_and_deploy_paths(self):
        self.assertTrue(find_forbidden([".github/workflows/ci.yml"]))
        self.assertTrue(find_forbidden(["deploy/prod.yaml"]))
        self.assertTrue(find_forbidden(["infra/main.tf"]))

    def test_project_extra_patterns(self):
        changed = ["legacy/old.py", "src/new.py"]
        self.assertEqual(find_forbidden(changed, ["legacy/*"]), ["legacy/old.py"])

    def test_clean_paths_pass(self):
        self.assertEqual(find_forbidden(["src/app.py", "tests/test_app.py"]), [])


class RedactTests(SimpleTestCase):
    def test_redacts_credentials_and_pii(self):
        text = "Authorization: Bearer abc123 user@example.com password=hunter2 token: s3cr3t"
        result = redact(text)
        for secret in ("abc123", "user@example.com", "hunter2", "s3cr3t"):
            self.assertNotIn(secret, result)

    def test_empty_input(self):
        self.assertEqual(redact(""), "")
