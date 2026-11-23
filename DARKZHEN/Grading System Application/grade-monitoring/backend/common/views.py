from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin

from .models import SystemConfig
from .serializers import SystemConfigSerializer


def public_config(config):
    return {
        "school_name": config.school_name,
        "short_name": config.short_name,
        "logo_url": config.logo_url,
        "default_school_year": config.default_school_year,
    }


class SchoolConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(public_config(SystemConfig.load()))


class SchoolConfigAdminView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        return Response(SystemConfigSerializer(SystemConfig.load()).data)

    def put(self, request):
        config = SystemConfig.load()
        serializer = SystemConfigSerializer(config, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SystemConfigSerializer(config).data)
