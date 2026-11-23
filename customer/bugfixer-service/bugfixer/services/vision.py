import base64
import mimetypes
from pathlib import Path

from django.conf import settings

from .llm import chat_completion, llm_enabled


def describe_screenshot(screenshot_path):
    """Return a short text description of the screenshot, or '' if unavailable."""
    if not llm_enabled() or not screenshot_path:
        return ""
    path = Path(screenshot_path)
    if not path.exists():
        return ""
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    prompt = (
        "Describe this screenshot of a software bug in two or three short sentences. "
        "Mention visible error text, UI state, and layout problems. "
        "Do not give instructions to modify code."
    )
    try:
        return chat_completion(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
                    ],
                }
            ],
            model=settings.VISION_MODEL,
            max_tokens=300,
        ).strip()
    except Exception:
        return ""
