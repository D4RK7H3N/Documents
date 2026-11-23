from django.urls import path

from .views import SchoolConfigView

urlpatterns = [
    path("school-config/", SchoolConfigView.as_view(), name="school-config"),
]
