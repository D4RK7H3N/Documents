from django.conf import settings
from django.http import HttpResponse

from .models import Project


class AllowedOriginCorsMiddleware:
    """Reflect CORS headers for registered widget origins or the dashboard origin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def _widget_origin(self, origin):
        if not origin:
            return False
        for project in Project.objects.filter(is_active=True).only("allowed_origins"):
            if origin in (project.allowed_origins or []):
                return True
        return False

    def __call__(self, request):
        origin = request.META.get("HTTP_ORIGIN")
        is_dashboard = bool(origin and settings.DASHBOARD_ORIGIN and origin == settings.DASHBOARD_ORIGIN)
        allowed = is_dashboard or self._widget_origin(origin)
        if request.method == "OPTIONS" and allowed:
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)
        if allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, X-Project-Key, X-CSRFToken"
            if is_dashboard:
                response["Access-Control-Allow-Credentials"] = "true"
            vary = response.get("Vary", "")
            if "Origin" not in vary:
                response["Vary"] = (vary + ", Origin").lstrip(", ")
        return response
