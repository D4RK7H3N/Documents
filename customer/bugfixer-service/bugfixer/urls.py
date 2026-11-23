from django.urls import path

from .views import ReportCreateView, ReportStatusView

urlpatterns = [
    path("reports/", ReportCreateView.as_view(), name="report-create"),
    path("reports/<int:pk>/", ReportStatusView.as_view(), name="report-status"),
]
