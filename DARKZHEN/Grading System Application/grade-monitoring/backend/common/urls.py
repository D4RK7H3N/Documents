from django.urls import path

from .views import SchoolConfigAdminView

urlpatterns = [
    path("admin/school-config/", SchoolConfigAdminView.as_view(), name="school-config-admin"),
]
