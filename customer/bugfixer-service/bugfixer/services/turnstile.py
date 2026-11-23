import requests
from django.conf import settings


def verify_turnstile(token, remote_ip=""):
    """Return True only when Cloudflare confirms the challenge."""
    if not token or not settings.TURNSTILE_SECRET_KEY:
        return False
    try:
        response = requests.post(
            settings.TURNSTILE_SITEVERIFY_URL,
            data={
                "secret": settings.TURNSTILE_SECRET_KEY,
                "response": token,
                "remoteip": remote_ip,
            },
            timeout=10,
        )
        response.raise_for_status()
        return bool(response.json().get("success"))
    except Exception:
        return False
