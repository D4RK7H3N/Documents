"""
URL configuration for School Configuration API.
"""
from django.urls import path
from .views import SchoolConfigView

urlpatterns = [
    path('current/', SchoolConfigView.as_view(), name='school-config-current'),
]