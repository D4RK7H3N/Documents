from django.urls import path

from .views import IngestStudentsView

urlpatterns = [
    path("integration/ingest/", IngestStudentsView.as_view(), name="integration-ingest"),
]
