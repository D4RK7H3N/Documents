from rest_framework.permissions import BasePermission


class HasIntegrationKey(BasePermission):
    message = "A valid X-Integration-Key header is required."

    def has_permission(self, request, view):
        from django.conf import settings

        key = settings.INTEGRATION_KEY
        if not key:
            return False
        provided = request.headers.get("X-Integration-Key", "")
        return bool(provided) and provided == key
