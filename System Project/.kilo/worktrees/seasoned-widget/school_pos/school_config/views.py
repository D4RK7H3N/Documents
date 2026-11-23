"""
API Views for School Configuration.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status
from .models import SchoolConfiguration
from .serializers import SchoolConfigurationSerializer, SchoolConfigurationUpdateSerializer


class SchoolConfigView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        config, _ = SchoolConfiguration.objects.get_or_create(pk=1)
        serializer = SchoolConfigurationSerializer(config, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        config, _ = SchoolConfiguration.objects.get_or_create(pk=1)
        serializer = SchoolConfigurationUpdateSerializer(config, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(SchoolConfigurationSerializer(config, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        config, _ = SchoolConfiguration.objects.get_or_create(pk=1)
        serializer = SchoolConfigurationUpdateSerializer(
            config,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(SchoolConfigurationSerializer(config, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)