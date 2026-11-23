from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.conf import settings
from django.shortcuts import redirect
from django.views.static import serve as static_serve


def root_redirect(request):
    """
    Root URL redirect based on user authentication status.
    """
    # Check authentication first
    if not request.user.is_authenticated:
        return redirect('staff:staff_login')
    
    # Check user type
    if request.user.is_superuser:
        return redirect('admin:index')
    elif request.user.is_staff:
        return redirect('staff:staff_dashboard')
    
    # Default to login
    return redirect('staff:staff_login')


def serve_media(request, path):
    """Serve uploaded media with hardening headers.

    NOTE: this endpoint is unauthenticated because <img src> cannot carry an
    Authorization header. It is deliberately NOT cacheable by shared caches
    (student photos/documents must not be stored on proxies/CDNs). Locking this
    down properly requires short-lived signed URLs - tracked as follow-up.
    """
    response = static_serve(request, path, document_root=settings.MEDIA_ROOT)
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Frame-Options"] = "DENY"
    response["Referrer-Policy"] = "no-referrer"
    # Neutralise active content (e.g. an uploaded SVG carrying script).
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    response["Cache-Control"] = "private, no-store, max-age=0"
    return response


urlpatterns = [
    # Root redirect - MUST BE FIRST
    path('', root_redirect, name='home'),
    
    # Admin panel
    path("admin/", admin.site.urls),
    
    # Staff app - includes all staff URLs (login, dashboard, etc.)
    path("staff/", include("staff.urls")),
    
    #api's
    path('api/', include('api.urls')),
    path('api/', include('school_config.urls')),  # School configuration API

    # Other apps
    path("students/", include("students.urls")),
    path("products/", include("products.urls")),
    path("sales/", include("sales.urls")),
    path("revenue/", include("revenue.urls")),
    path("payments/", include("payments.urls")),
    path("cashier/", include("cashier.urls")),
    path("dorm/", include("dorm.urls")),
    path("tours/", include("tours.urls")),
    path("assessment/", include("assessment.urls")),
    path("graduation/", include("graduation.urls")),
]

# Media must be served in production too: <img src> cannot send an
# Authorization header, so assets cannot live behind token auth.
urlpatterns += [
    re_path(rf"^{settings.MEDIA_URL.lstrip('/')}(?P<path>.*)$", serve_media),
]

# Serve static files in development)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])