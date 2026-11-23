import hmac
import logging

from django.db import connection
from django.http import JsonResponse
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BugReport, Project
from .serializers import ReportCreateSerializer, ReportStatusSerializer
from .services.client_ip import get_client_ip
from .services.turnstile import verify_turnstile
from .throttles import ReportIPThrottle, ReportKeyThrottle

logger = logging.getLogger("bugfixer")


def health(request):
    """Liveness + DB connectivity. Deliberately returns no sensitive details."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


class ReportCreateView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ReportIPThrottle, ReportKeyThrottle]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        key = request.META.get("HTTP_X_PROJECT_KEY", "")
        project = Project.objects.filter(public_key=key, is_active=True).first()
        if not project:
            return Response({"detail": "Invalid or inactive project key."}, status=401)

        origin = request.META.get("HTTP_ORIGIN", "")
        if origin not in (project.allowed_origins or []):
            return Response({"detail": "Origin is not allowed for this project."}, status=403)

        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(project=project)
        return Response(
            {"id": report.pk, "status": report.status, "status_token": report.status_token},
            status=201,
        )


class ReportStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk):
        token = request.query_params.get("token", "")
        if not str(pk).isdigit() or not token:
            return Response({"detail": "Not found."}, status=404)
        report = BugReport.objects.filter(pk=pk).first()
        if report is None or not hmac.compare_digest(report.status_token, token):
            return Response({"detail": "Not found."}, status=404)
        return Response(ReportStatusSerializer(report).data)
