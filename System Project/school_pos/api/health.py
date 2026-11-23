import logging

from django.db import connection, OperationalError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

# Populated on first success so the DB is only probed once per process instead
# of opening a fresh connection on every unauthenticated request.
_db_ok = None


@require_GET
@never_cache
def health_check(request):
    """Liveness endpoint.

    Public and unauthenticated by design, so it deliberately reports only
    whether the process is up. Detailed state (including database reachability)
    is available to operators via the authenticated /api/auth/me endpoint or
    the gateway's token-protected /__gateway/metrics.
    """
    return JsonResponse({"status": "ok"}, status=200)


@require_GET
@never_cache
def readiness_check(request):
    """Readiness probe that actually touches the database.

    Not routed by default. Wire to an internal-only path (or require a shared
    secret header) before exposing it.
    """
    global _db_ok
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        _db_ok = True
    except OperationalError:
        _db_ok = False
        logger.warning("readiness probe: database unreachable")

    return JsonResponse(
        {"status": "ok" if _db_ok else "error", "db": _db_ok},
        status=200 if _db_ok else 503,
    )
