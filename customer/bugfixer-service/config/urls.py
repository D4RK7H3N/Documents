from django.contrib import admin
from django.urls import include, path

from bugfixer.views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("bugfixer.urls")),
    path("api/dashboard/", include("bugfixer.dashboard_api.urls")),
]
