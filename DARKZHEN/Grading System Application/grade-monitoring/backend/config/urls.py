from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve as static_serve


def health(request):
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False
    return JsonResponse({"status": "ok" if db_ok else "degraded", "db": "ok" if db_ok else "error"})


urlpatterns = [
    path("health/", health),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls_auth")),
    path(
        "api/v1/",
        include(
            [
                path("", include("accounts.urls")),
                path("", include("academics.urls")),
                path("", include("grading.urls")),
                path("", include("audit.urls")),
                path("", include("integration.urls")),
                path("", include("common.urls")),
                path("", include("common.urls_public")),
            ]
        ),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    WEB_DIST = settings.BASE_DIR.parent / "web" / "dist"

    def spa(request, path="index.html"):
        return static_serve(request, "index.html", document_root=str(WEB_DIST))

    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", static_serve, {"document_root": str(WEB_DIST / "assets")}),
        re_path(r"^logo\.svg$", static_serve, {"path": "logo.svg", "document_root": str(WEB_DIST)}),
        re_path(r"^(?!api/|admin/|health/|media/|static/).*$", spa),
    ]
