import mimetypes
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import FileResponse, Http404
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import BugReport, Project, Status, new_public_key
from ..services import report_actions
from .serializers import (
    LoginSerializer,
    ProjectSerializer,
    ReportDetailSerializer,
    ReportListSerializer,
)


class DashboardAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]


class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "ok", "csrfToken": get_token(request)})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_staff:
            return Response({"detail": "Invalid credentials."}, status=401)
        login(request, user)
        get_token(request)
        return Response({"id": user.pk, "username": user.username, "is_staff": user.is_staff})


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"detail": "ok"})


class MeView(DashboardAPIView):
    def get(self, request):
        user = request.user
        return Response({"id": user.pk, "username": user.username, "is_staff": user.is_staff})


class ProjectListView(DashboardAPIView):
    def get(self, request):
        return Response(ProjectSerializer(Project.objects.all(), many=True).data)

    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        return Response(ProjectSerializer(project).data, status=201)


class ProjectDetailView(DashboardAPIView):
    def get(self, request, pk):
        return Response(ProjectSerializer(get_object_or_404(Project, pk=pk)).data)

    def patch(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project.delete()
        return Response(status=204)


class RotateKeyView(DashboardAPIView):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project.public_key = new_public_key()
        project.save(update_fields=["public_key", "updated_at"])
        return Response(ProjectSerializer(project).data)


class ReportPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class ReportListView(DashboardAPIView):
    def get(self, request):
        queryset = BugReport.objects.select_related("project").all()
        params = request.query_params
        if params.get("project"):
            queryset = queryset.filter(project_id=params["project"])
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("classification"):
            queryset = queryset.filter(classification__icontains=params["classification"])
        if params.get("search"):
            queryset = queryset.filter(message__icontains=params["search"])
        date_from = parse_date(params.get("date_from", "") or "")
        date_to = parse_date(params.get("date_to", "") or "")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        ordering = params.get("ordering", "-created_at")
        if ordering.lstrip("-") not in {"created_at", "updated_at", "status", "id"}:
            ordering = "-created_at"
        queryset = queryset.order_by(ordering)
        paginator = ReportPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = ReportListSerializer(page, many=True).data
        if page is not None:
            return paginator.get_paginated_response(data)
        return Response(data)


class ReportDetailView(DashboardAPIView):
    def get(self, request, pk):
        report = get_object_or_404(BugReport.objects.select_related("project"), pk=pk)
        return Response(ReportDetailSerializer(report).data)


class ReportRequeueView(DashboardAPIView):
    def post(self, request, pk):
        report = get_object_or_404(BugReport, pk=pk)
        report_actions.requeue(BugReport.objects.filter(pk=report.pk))
        report.refresh_from_db()
        return Response(ReportDetailSerializer(report).data)


class ReportRejectView(DashboardAPIView):
    def post(self, request, pk):
        report = get_object_or_404(BugReport, pk=pk)
        report_actions.reject(BugReport.objects.filter(pk=report.pk))
        report.refresh_from_db()
        return Response(ReportDetailSerializer(report).data)


class ReportApprovePRView(DashboardAPIView):
    def post(self, request, pk):
        report = get_object_or_404(BugReport.objects.select_related("project"), pk=pk)
        result = report_actions.approve_pr(BugReport.objects.filter(pk=report.pk))
        report.refresh_from_db()
        payload = {"result": result, "report": ReportDetailSerializer(report).data}
        return Response(payload, status=200 if not result["failed"] else 400)


class ReportScreenshotView(DashboardAPIView):
    def get(self, request, pk):
        report = get_object_or_404(BugReport, pk=pk)
        if not report.screenshot:
            raise Http404
        content_type = mimetypes.guess_type(report.screenshot.name)[0] or "application/octet-stream"
        return FileResponse(report.screenshot.open("rb"), content_type=content_type)


class StatsView(DashboardAPIView):
    def get(self, request):
        reports = BugReport.objects.all()
        counts = {choice: reports.filter(status=choice).count() for choice in Status.values}

        today = timezone.localdate()
        per_day = []
        for offset in range(29, -1, -1):
            day = today - timedelta(days=offset)
            per_day.append(
                {"date": day.isoformat(), "count": reports.filter(created_at__date=day).count()}
            )

        fix_seconds = [
            (r.updated_at - r.created_at).total_seconds()
            for r in reports.filter(status=Status.FIX_READY)
        ]
        avg_time_to_fix = sum(fix_seconds) / len(fix_seconds) if fix_seconds else 0

        per_project = []
        for project in Project.objects.all():
            project_reports = reports.filter(project=project)
            terminal = project_reports.filter(
                status__in=[Status.FIX_READY, Status.FAILED, Status.REJECTED]
            ).count()
            fixed = project_reports.filter(status=Status.FIX_READY).count()
            per_project.append(
                {
                    "project_id": project.pk,
                    "name": project.name,
                    "total": project_reports.count(),
                    "fixed": fixed,
                    "success_rate": round(100 * fixed / terminal, 1) if terminal else 0,
                }
            )

        return Response(
            {
                "status_counts": counts,
                "reports_per_day": per_day,
                "avg_time_to_fix_seconds": round(avg_time_to_fix),
                "per_project": per_project,
            }
        )


class SettingsView(DashboardAPIView):
    def get(self, request):
        return Response(
            {
                "llm_key_set": bool(settings.LLM_API_KEY),
                "github_token_set": bool(settings.GITHUB_TOKEN),
                "smtp_set": bool(settings.SMTP_HOST),
                "turnstile_set": bool(settings.TURNSTILE_SECRET_KEY),
                "cf_access_enabled": bool(settings.CF_ACCESS_ENABLED),
                "use_r2": bool(settings.USE_R2),
                "r2_bucket_set": bool(settings.R2_BUCKET),
                "dashboard_origin_set": bool(settings.DASHBOARD_ORIGIN),
                "widget_url_set": bool(settings.WIDGET_URL),
                "debug": bool(settings.DEBUG),
            }
        )
