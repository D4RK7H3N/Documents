from django.urls import path

from .views import (
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    ProjectDetailView,
    ProjectListView,
    ReportApprovePRView,
    ReportDetailView,
    ReportListView,
    ReportRejectView,
    ReportRequeueView,
    ReportScreenshotView,
    RotateKeyView,
    SettingsView,
    StatsView,
)

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="dashboard-csrf"),
    path("auth/login/", LoginView.as_view(), name="dashboard-login"),
    path("auth/logout/", LogoutView.as_view(), name="dashboard-logout"),
    path("auth/me/", MeView.as_view(), name="dashboard-me"),
    path("projects/", ProjectListView.as_view(), name="dashboard-projects"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="dashboard-project-detail"),
    path("projects/<int:pk>/rotate-key/", RotateKeyView.as_view(), name="dashboard-rotate-key"),
    path("reports/", ReportListView.as_view(), name="dashboard-reports"),
    path("reports/<int:pk>/", ReportDetailView.as_view(), name="dashboard-report-detail"),
    path("reports/<int:pk>/screenshot/", ReportScreenshotView.as_view(), name="dashboard-screenshot"),
    path("reports/<int:pk>/requeue/", ReportRequeueView.as_view(), name="dashboard-requeue"),
    path("reports/<int:pk>/reject/", ReportRejectView.as_view(), name="dashboard-reject"),
    path("reports/<int:pk>/approve-pr/", ReportApprovePRView.as_view(), name="dashboard-approve-pr"),
    path("stats/", StatsView.as_view(), name="dashboard-stats"),
    path("settings/", SettingsView.as_view(), name="dashboard-settings"),
]
