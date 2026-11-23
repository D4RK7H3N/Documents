from django.shortcuts import redirect
from datetime import timedelta
from django.utils import timezone

import re

# Only sane device ids: 8-64 chars of letters, digits and a few separators,
# so a crafted header can never inject anything weird into the DB.
_DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9._:\-]{8,64}$")

# How often a terminal's last_seen_at may be refreshed, so every API call
# from an idle cashier does not turn into a write.
_LAST_SEEN_THROTTLE = timedelta(seconds=60)


def resolve_terminal(request):
    """Return the Terminal matching this request's X-Device-Id header,
    registering unknown devices on first sight.

    When the app sends X-Device-Previous-Id (it changed from the OS machine
    GUID to a per-installation UUID), the existing terminal is moved onto the
    new id so its name and sales history stay attached to this machine.

    Returns None when the header is missing or malformed so that a sale or
    payment is never blocked by device-identity problems; those rows simply
    land in the "Unassigned" bucket of the revenue report.
    """
    from sales.models import Terminal

    device_id = (request.headers.get("X-Device-Id") or "").strip()
    if not device_id or not _DEVICE_ID_RE.match(device_id):
        return None

    # Migration: this machine used to be known by another id.
    previous_id = (request.headers.get("X-Device-Previous-Id") or "").strip()
    if previous_id and previous_id != device_id and _DEVICE_ID_RE.match(previous_id):
        old = Terminal.objects.filter(device_id=previous_id).first()
        if old and not Terminal.objects.filter(device_id=device_id).exists():
            old.device_id = device_id
            old.save(update_fields=["device_id"])

    terminal, created = Terminal.objects.get_or_create(
        device_id=device_id,
        defaults={"name": f"Device {device_id[-6:]}"},
    )

    now = timezone.now()
    if (
        created
        or terminal.last_seen_at is None
        or (now - terminal.last_seen_at) > _LAST_SEEN_THROTTLE
    ):
        terminal.last_seen_at = now
        terminal.save(update_fields=["last_seen_at"])

    return terminal


class DeviceTerminalMiddleware:
    """Auto-register devices that call the API, so admins can name terminals
    in Django admin before the first sale arrives from them."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            request.path.startswith("/api/")
            and user is not None
            and user.is_authenticated
        ):
            try:
                resolve_terminal(request)
            except Exception:
                # Terminal registration must never take an API call down.
                pass
        return self.get_response(request)


class StaffAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that don't require authentication
        self.exempt_paths = [
            '/staff/login/',
            '/staff/register/',
            '/admin/',        # Django admin (includes /admin/login/)
            '/static/',
            '/media/',
            '/api/',          # API endpoints should handle their own auth
            '/releases/',     # self-hosted installer feed for auto-update
        ]

    def __call__(self, request):
        # Check if path is exempt
        path = request.path
        is_exempt = any(path.startswith(exempt) for exempt in self.exempt_paths)
        
        # CRITICAL FIX: Don't redirect if it's a POST to login (form submission)
        if path == '/staff/login/' and request.method == 'POST':
            # Let the login view handle the POST request
            response = self.get_response(request)
            return response
        
        # If not exempt and not authenticated, redirect to staff login
        if not is_exempt and not request.user.is_authenticated:
            # Don't redirect if already on login page
            if path != '/staff/login/':
                return redirect('/staff/login/')
        
        response = self.get_response(request)
        return response


class ResponseHeaderSanitizerMiddleware:
    """Mission P5 - strip backend fingerprint headers from every response.

    Placed first in MIDDLEWARE so its response phase runs last, after
    SecurityMiddleware / WhiteNoise / XFrameOptions have added their headers.
    """

    STRIP = ("Server", "X-Powered-By", "Via")

    # Staff portal and Django admin rely on inline <script>/<style> blocks;
    # the strict SPA policy is applied by the sms-3 Worker instead.
    STAFF_CSP = (
        "default-src 'self'; "
        # Cloudflare Web Analytics injects its beacon on every proxied HTML
        # page; allow that single origin instead of weakening script-src.
        "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "font-src 'self' data: https:; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for name in self.STRIP:
            if name in response.headers:
                del response.headers[name]
        # Behind the Cloudflare tunnel Django does not always see the request
        # as secure, so SecurityMiddleware skips HSTS. The edge is always
        # HTTPS; set it explicitly for both HTML and API responses.
        if "Strict-Transport-Security" not in response.headers:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if response.get("Content-Type", "").startswith("text/html"):
            if "Content-Security-Policy" not in response.headers:
                response.headers["Content-Security-Policy"] = self.STAFF_CSP
        return response