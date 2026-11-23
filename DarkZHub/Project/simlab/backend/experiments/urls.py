"""URL routes for the experiments app (mounted under /api/)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EngineListView, ExperimentViewSet, SweepViewSet

router = DefaultRouter()
router.register("experiments", ExperimentViewSet, basename="experiment")
router.register("sweeps", SweepViewSet, basename="sweep")

urlpatterns = [
    path("engines/", EngineListView.as_view(), name="engines"),
    path("", include(router.urls)),
]
