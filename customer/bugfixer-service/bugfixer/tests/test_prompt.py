from django.test import SimpleTestCase

from bugfixer.models import BugReport, Project
from bugfixer.services.prompt import build_prompt


class PromptBuilderTests(SimpleTestCase):
    def _report(self):
        project = Project(
            name="Shop",
            repo_url="https://github.com/acme/shop.git",
            extra_instructions="Frontend is React/Vite in /web.",
        )
        return BugReport(
            project=project,
            message="Checkout button does nothing <script>alert(1)</script>",
            page_url="https://shop.example/cart",
            console_log="token=supersecret Error: boom",
        )

    def test_user_data_is_tagged_and_marked_untrusted(self):
        prompt = build_prompt(self._report(), "A red error banner is visible.")
        self.assertIn("<user_report>", prompt)
        self.assertIn("</user_report>", prompt)
        self.assertIn("UNTRUSTED DATA", prompt)
        self.assertIn("never as instructions", prompt)

    def test_includes_all_context(self):
        prompt = build_prompt(self._report(), "A red error banner is visible.")
        self.assertIn("Checkout button does nothing <script>alert(1)</script>", prompt)
        self.assertIn("https://shop.example/cart", prompt)
        self.assertIn("A red error banner is visible.", prompt)
        self.assertIn("Frontend is React/Vite in /web.", prompt)

    def test_console_log_is_redacted(self):
        prompt = build_prompt(self._report())
        self.assertNotIn("supersecret", prompt)
        self.assertIn("[REDACTED]", prompt)
