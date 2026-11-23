from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView
from rest_framework.mixins import DestroyModelMixin
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.serializers import UserSerializer
from common.pagination import StandardPagination
from common.permissions import IsAdmin, IsAuthenticatedActive, IsTeacher

from .models import ClassAssignment, Section, StudentProfile, Subject
from .serializers import (
    ClassAssignmentSerializer,
    SectionSerializer,
    StudentCreateSerializer,
    StudentProfileSerializer,
    StudentUpdateSerializer,
    SubjectSerializer,
    create_staff_account,
    create_student,
    import_students_csv,
)


class TeacherClassesView(ListAPIView):
    serializer_class = ClassAssignmentSerializer
    permission_classes = [IsTeacher]
    pagination_class = StandardPagination

    def get_queryset(self):
        return ClassAssignment.objects.filter(teacher=self.request.user).select_related(
            "subject", "section", "teacher"
        )


class GuardedDestroyMixin(DestroyModelMixin):
    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"error": {"code": "conflict", "message": "This record is referenced by other data and cannot be deleted."}},
                status=status.HTTP_409_CONFLICT,
            )


class StudentViewSet(GuardedDestroyMixin, viewsets.ModelViewSet):
    queryset = StudentProfile.objects.select_related("user", "section").all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardPagination
    http_method_names = ["get", "post", "patch", "head", "options"]

    def create(self, request, *args, **kwargs):
        serializer = StudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, password = create_student(
            lrn=serializer.validated_data["lrn"],
            full_name=serializer.validated_data["full_name"],
            section_id=serializer.validated_data["section"],
            created_by=request.user,
        )
        data = StudentProfileSerializer(profile).data
        data["temporary_password"] = password
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = StudentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, changes = serializer.save(profile=profile, actor=request.user)
        data = StudentProfileSerializer(profile).data
        data["changed"] = changes
        return Response(data)


class StudentImportView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": {"code": "validation_error", "message": "Attach a CSV file in the 'file' field."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        results, errors = import_students_csv(file=file, created_by=request.user)
        if results is None:
            return Response(
                {"error": {"code": "validation_error", "message": errors[0]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"imported": results, "errors": errors}, status=status.HTTP_201_CREATED)


class SectionViewSet(GuardedDestroyMixin, viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardPagination


class SubjectViewSet(GuardedDestroyMixin, viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardPagination


class AssignmentViewSet(GuardedDestroyMixin, viewsets.ModelViewSet):
    queryset = ClassAssignment.objects.select_related("subject", "section", "teacher").all()
    serializer_class = ClassAssignmentSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


class TeacherPickerView(APIView):
    permission_classes = [IsAuthenticatedActive]

    def get(self, request):
        from accounts.serializers import UserSerializer

        teachers = User.objects.filter(role=User.Role.TEACHER, is_active=True).order_by("username")
        return Response(UserSerializer(teachers, many=True).data)


class TeacherConfigView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        teachers = User.objects.filter(role=User.Role.TEACHER).order_by("username")
        assignments = ClassAssignment.objects.select_related("subject", "section").filter(
            teacher__in=teachers
        )
        by_teacher = {}
        for a in assignments:
            by_teacher.setdefault(a.teacher_id, []).append(
                {
                    "id": a.id,
                    "subject": a.subject.name,
                    "section": a.section.name,
                    "grade_level": a.section.grade_level,
                    "school_year": a.school_year,
                }
            )
        return Response(
            [
                {
                    "id": t.id,
                    "username": t.username,
                    "display_name": t.display_name,
                    "is_active": t.is_active,
                    "must_change_password": t.must_change_password,
                    "assignments": by_teacher.get(t.id, []),
                }
                for t in teachers
            ]
        )


class UserListView(ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardPagination
    queryset = User.objects.order_by("username")

    def get_queryset(self):
        qs = User.objects.order_by("username")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs
