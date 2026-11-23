from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasIntegrationKey
from .services import IngestSerializer, ingest_students


class IngestStudentsView(APIView):
    permission_classes = [AllowAny, HasIntegrationKey]

    def post(self, request):
        serializer = IngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = ingest_students(serializer.validated_data["students"])
        return Response(report)
