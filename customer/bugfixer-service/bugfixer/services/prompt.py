from pathlib import Path

from django.template import Context, Template

from .guards import redact

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "prompt.md"


def build_prompt(report, screenshot_description=""):
    """Render the agent prompt. All user-controlled data is passed as context."""
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.render(
        Context(
            {
                "message": report.message,
                "page_url": report.page_url or "(not provided)",
                "console_log": redact(report.console_log) or "(none provided)",
                "screenshot_description": screenshot_description or "(no screenshot description available)",
                "extra_instructions": report.project.extra_instructions or "(none provided)",
            },
            autoescape=False,
        )
    )
