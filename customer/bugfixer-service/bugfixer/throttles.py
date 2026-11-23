from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

from .services.client_ip import get_client_ip


class ConfiguredRateThrottle(SimpleRateThrottle):
    """Read the rate from Django settings so it can be overridden in tests."""

    scope = None

    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        if self.scope in rates:
            return rates[self.scope]
        return super().get_rate()


class ReportIPThrottle(ConfiguredRateThrottle):
    scope = "report_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": get_client_ip(request)}


class ReportKeyThrottle(ConfiguredRateThrottle):
    scope = "report_key"

    def get_cache_key(self, request, view):
        key = request.META.get("HTTP_X_PROJECT_KEY")
        if not key:
            return None
        return self.cache_format % {"scope": self.scope, "ident": key}
