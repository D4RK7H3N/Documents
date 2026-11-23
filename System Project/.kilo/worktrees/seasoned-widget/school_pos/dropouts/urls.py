from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DropoutViewSet

router = DefaultRouter()
router.register(r'', DropoutViewSet, basename='dropout')

urlpatterns = [
    path('', include(router.urls)),
]