from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.contrib.auth.password_validation import validate_password
from importlib import import_module
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)
from openpyxl import load_workbook
import io

from students.models import Student, StudentDocument, StudentData
from staff.models import StaffProfile
from dorm.models import DormBuilding, DormRoom, DormAssignment, DormPayment
from sales.models import Sale, SaleItem
from products.models import Product
from tuition.models import TuitionPayment
from assessment.models import AssessmentType, StudentAssessment, AssessmentPayment
from tours.models import EducationalTour, TourEnrollment, TourPayment
from graduation.models import GraduationEvent, StudentGraduation, GraduationPayment
from payments.models import Payment


def _or_no(ref, date_value, fallback_id):
    """Use stored reference; fallback to OR-YYYY-NNNNN from date + id.

    Module level so both RevenueViewSet.list() and RevenueViewSet.report()
    can use it (it was previously nested inside list(), which made report()
    raise NameError).
    """
    if ref:
        return ref
    try:
        yr = date_value.year
    except Exception:
        yr = timezone.now().year
    return f"OR-{yr}-{int(fallback_id):05d}"
from .serializers import (
    StudentSerializer,
    StudentDetailSerializer,
    StudentDocumentSerializer,
    StudentDataSerializer,
    StudentChargeSerializer,
    DormBuildingSerializer,
    DormRoomSerializer,
    DormAssignmentSerializer,
    DormPaymentSerializer,
    ProductSerializer,
    SaleSerializer,
    SaleCreateSerializer,
    TuitionPaymentSerializer,
    TuitionRecordSerializer,
    AssessmentTypeSerializer,
    StudentAssessmentSerializer,
    AssessmentPaymentSerializer,
    EducationalTourSerializer,
    TourEnrollmentSerializer,
    TourPaymentSerializer,
    GraduationEventSerializer,
    StudentGraduationSerializer,
    GraduationPaymentSerializer,
)


class LoginRateThrottle(AnonRateThrottle):
    rate = "10/hour"


class LoginViewSet(viewsets.ViewSet):
    """User login endpoint with case-insensitive username support"""

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Revoke the caller's API token server-side.

        Previously logout only cleared localStorage on the client, which left
        the token valid forever on the server (DRF tokens have no expiry).
        """
        Token.objects.filter(user=request.user).delete()
        return Response({"message": "Logged out"})

    @action(detail=False, methods=["post"])
    def login(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "").strip()

        if not username or not password:
            return Response(
                {"error": "Username and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # FIXED: Case-insensitive username lookup
        try:
            # Find user with case-insensitive username
            user_obj = User.objects.get(username__iexact=username)

            # Authenticate with the ACTUAL username (case-sensitive stored version)
            user = authenticate(request, username=user_obj.username, password=password)

            if user is None:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Create or get token
            token, _ = Token.objects.get_or_create(user=user)

            profile = getattr(user, "staff_profile", None)

            return Response(
                {
                    "token": token.key,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        # Profile name travels with every login so printed
                        # documents can use it as the prepared-by name
                        # without a separate profile fetch.
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "is_staff": user.is_staff,
                        "is_superuser": user.is_superuser,
                        "avatar": profile.avatar if profile else None,
                        "has_seen_onboarding": profile.has_seen_onboarding if profile else False,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )
        except User.MultipleObjectsReturned:
            # Handle edge case of duplicate usernames
            return Response(
                {"error": "Multiple users found. Please contact admin."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """Get current user profile"""
        user = request.user
        profile = getattr(user, "staff_profile", None)
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined,
                "avatar": profile.avatar if profile else None,
                "has_seen_onboarding": profile.has_seen_onboarding if profile else None,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update current user profile"""
        user = request.user
        profile, _ = StaffProfile.objects.get_or_create(user=user)

        if "email" in request.data:
            old_password = request.data.get("old_password")
            if not old_password:
                return Response(
                    {"error": "Current password is required to change email"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not user.check_password(old_password):
                return Response(
                    {"error": "Current password is incorrect"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.email = request.data["email"]

        if "first_name" in request.data:
            user.first_name = request.data["first_name"]
        if "last_name" in request.data:
            user.last_name = request.data["last_name"]
        if "avatar" in request.data:
            profile.avatar = request.data["avatar"]
        if "has_seen_onboarding" in request.data:
            profile.has_seen_onboarding = request.data["has_seen_onboarding"]

        user.save()
        profile.save()

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "avatar": profile.avatar,
                "has_seen_onboarding": profile.has_seen_onboarding,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Change user password"""
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response(
                {"error": "Both old_password and new_password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify old password
        if not user.check_password(old_password):
            return Response(
                {"error": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Enforce AUTH_PASSWORD_VALIDATORS. Calling set_password() directly
        # bypasses them (they only run in Django's forms), which allowed
        # setting a 1-character password via the API.
        try:
            validate_password(new_password, user)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        # Update token
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response(
            {"message": "Password changed successfully", "token": token.key},
            status=status.HTTP_200_OK,
        )


class StudentViewSet(viewsets.ModelViewSet):
    """Student CRUD operations"""

    queryset = Student.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Ordered so PageNumberPagination cannot return inconsistent pages
        # (it warns and can repeat/skip rows on an unordered queryset).
        queryset = Student.objects.all().order_by("-id")

        # Check if we should include dropout/inactive students
        include_inactive = (
            self.request.query_params.get("include_inactive", "false").lower() == "true"
        )

        # Hide inactive students from the LIST endpoint only. Applying this to
        # every action broke get_object(): retrieve/update/partial_update on a
        # dropout returned 404 "No Student matches the given query.", so
        # editing a dropout record failed.
        if self.action == "list" and not include_inactive:
            queryset = queryset.exclude(
                status__in=["Drop-out", "Inactive", "Transferred"]
            )

        # Also filter by search if provided
        search = self.request.query_params.get("search", "")
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(lrn__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return StudentDetailSerializer
        return StudentSerializer

    def perform_update(self, serializer):
        """Override update to keep current_grade_level in sync with shs_grade/college_year and tracking graduation status"""
        instance = serializer.instance

        old_shs_grade = instance.shs_grade
        old_college_year = instance.college_year
        old_enrollment_status = getattr(instance, 'enrollment_status', None)

        student = serializer.save()

        # Some clients (e.g. the Students edit form) send `current_grade_level`
        # instead of the raw grade columns. That field is not writable on the
        # serializer, so it was being dropped and current_grade_level was then
        # recomputed from the stale shs_grade/college_year - silently undoing
        # the change the user just made. Mirror the incoming label onto the raw
        # columns so the derived value below reflects the requested grade.
        try:
            incoming_grade = self.request.data.get("current_grade_level")
        except Exception:
            incoming_grade = None
        if incoming_grade:
            import re as _re

            # Unanchored: the label is usually "Grade 12" (number is not the
            # first character) or "1st Year Bundled" (number is).
            m = _re.search(r"(\d+)", str(incoming_grade))
            if m:
                num = m.group(1)
                if _re.search(r"year", str(incoming_grade), _re.IGNORECASE):
                    student.college_year = num
                    if student.level_type == "SHS":
                        student.shs_grade = None
                else:
                    student.shs_grade = num
                    if student.level_type in ("BUN", "COL"):
                        student.college_year = None

        new_shs_grade = student.shs_grade
        new_college_year = student.college_year
        new_enrollment_status = getattr(student, 'enrollment_status', None)

        try:
            if student.level_type == "SHS":
                if new_shs_grade == "12":
                    student.current_grade_level = "Grade 12"
                elif new_shs_grade == "11":
                    student.current_grade_level = "Grade 11"
                elif new_shs_grade:
                    student.current_grade_level = f"Grade {new_shs_grade}"
                else:
                    # No SHS grade set (e.g. switched to a year level):
                    # leave the existing value alone rather than writing
                    # "Grade None".
                    student.current_grade_level = (
                        student.current_grade_level or "N/A"
                    )

                if old_enrollment_status != "Graduated" and new_enrollment_status == "Graduated":
                    pass
            elif student.level_type in ("BUN", "COL"):
                if new_college_year == "1":
                    student.current_grade_level = "1st Year Tesda Accredited" if student.level_type == "BUN" else "College 1st Year"
                elif new_college_year == "2":
                    student.current_grade_level = "2nd Year Tesda Accredited" if student.level_type == "BUN" else "College 2nd Year"
                elif new_college_year in ("3", "4"):
                    ordinal = "3rd" if new_college_year == "3" else "4th"
                    student.current_grade_level = f"College {ordinal} Year"

            if (student.level_type == "SHS"
                and old_shs_grade != new_shs_grade
                and new_shs_grade in ("11", "12")
            ) or (student.level_type in ("BUN", "COL")
                  and old_college_year != new_college_year
                  and new_college_year in ("1", "2", "3", "4")
            ):
                old_level = f"Grade {old_shs_grade}" if student.level_type == "SHS" else (
                    "1st Year Tesda Accredited" if old_college_year == "1" else
                    "2nd Year Tesda Accredited" if old_college_year == "2" else
                    "College 3rd Year" if old_college_year == "3" else
                    "College 4th Year" if old_college_year == "4" else None
                )

            custom = student.custom_tuition_fee or 0
            if custom > 0:
                total_paid = sum(
                    float(p.amount or 0)
                    for p in student.tuition_payments.all()
                )
                new_balance = float(custom) - total_paid
                if new_balance < 0:
                    new_balance = 0
                student.tuition_balance = new_balance

            student.save()
        except Exception as e:
            logger.exception(
                "Error syncing current_grade_level/tuition_balance "
                "for student_id=%s exc=%s",
                getattr(student, "id", None),
                type(e).__name__,
            )

        try:
            if student.level_type == "SHS":
                if old_shs_grade == "11" and student.shs_grade == "12":
                    current_balance = (
                        Decimal(str(student.tuition_balance))
                        if student.tuition_balance
                        else Decimal("0")
                    )
                    was_payee = current_balance > 0 or (
                        hasattr(student, "tuition_fee")
                        and student.tuition_fee
                        and student.tuition_fee > 0
                    )
                    # Promotion no longer invents a fee. The student's own
                    # custom_tuition_fee is carried forward; tuition for the new
                    # year is set explicitly on the student record.
                    if was_payee and student.custom_tuition_fee:
                        student.tuition_balance = (
                            Decimal(str(student.custom_tuition_fee))
                            - sum(
                                Decimal(str(p.amount or 0))
                                for p in student.tuition_payments.all()
                            )
                        )
                        if student.tuition_balance < 0:
                            student.tuition_balance = Decimal("0")
                    student.enrollment_status = "Continuing"
                    student.save()
            elif student.level_type == "BUN":
                if old_college_year == "1" and student.college_year == "2":
                    current_balance = (
                        Decimal(str(student.tuition_balance))
                        if student.tuition_balance
                        else Decimal("0")
                    )
                    was_payee = current_balance > 0 or (
                        hasattr(student, "tuition_fee")
                        and student.tuition_fee
                        and student.tuition_fee > 0
                    )
                    # Promotion no longer invents a fee (see SHS branch above).
                    if was_payee and student.custom_tuition_fee:
                        student.tuition_balance = (
                            Decimal(str(student.custom_tuition_fee))
                            - sum(
                                Decimal(str(p.amount or 0))
                                for p in student.tuition_payments.all()
                            )
                        )
                        if student.tuition_balance < 0:
                            student.tuition_balance = Decimal("0")
                    student.enrollment_status = "Continuing"
                    student.save()
            elif student.level_type == "COL":
                if old_college_year != student.college_year and student.college_year in ("2", "3", "4"):
                    student.enrollment_status = "Continuing"
                    student.save()
        except Exception as e:
            logger.exception(
                "Error auto-updating tuition during promotion exc=%s",
                type(e).__name__,
            )

    @action(detail=True, methods=["post"])
    def upload_document(self, request, pk=None):
        """Upload document for student"""
        student = self.get_object()
        file = request.FILES.get("file")
        document_type = request.data.get("document_type")

        if not file or not document_type:
            return Response(
                {"error": "file and document_type required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            return Response(
                {"error": "File size exceeds 10MB limit"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for duplicate document type
        existing = StudentDocument.objects.filter(
            student=student, document_type=document_type
        ).first()

        if existing:
            # Check if the file is actually different
            if existing.file and existing.file.name == file.name:
                return Response(
                    {
                        "error": f'Document of type "{document_type}" already exists for this student with the same filename. Please upload a different file.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Replace existing document
            existing.file = file
            existing.description = request.data.get("description", "")
            existing.save()
            return Response(
                StudentDocumentSerializer(existing).data, status=status.HTTP_200_OK
            )

        document = StudentDocument.objects.create(
            student=student,
            document_type=document_type,
            file=file,
            description=request.data.get("description", ""),
        )

        return Response(
            StudentDocumentSerializer(document).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get"])
    def documents(self, request, pk=None):
        """Get all documents for student"""
        student = self.get_object()
        documents = student.documents.all()
        serializer = StudentDocumentSerializer(documents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "put"])
    def enrollment_data(self, request, pk=None):
        """Get or update enrollment data"""
        student = self.get_object()
        enrollment_data, _ = StudentData.objects.get_or_create(student=student)

        if request.method == "PUT":
            serializer = StudentDataSerializer(
                enrollment_data, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = StudentDataSerializer(enrollment_data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search students by LRN, name, or email"""
        query = request.query_params.get("q", "")

        if not query:
            return Response(
                {"error": "q parameter required"}, status=status.HTTP_400_BAD_REQUEST
            )

        students = Student.objects.filter(
            Q(lrn__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get student statistics"""
        total_students = Student.objects.count()

        # Safe query for enrollment_status
        active_students = (
            Student.objects.filter(enrollment_status="Active").count()
            if hasattr(Student, "enrollment_status")
            else 0
        )

        active_dorm = DormAssignment.objects.filter(status="Active").count()

        # Safe query for tuition_balance
        total_balance = (
            Student.objects.aggregate(Sum("tuition_balance"))["tuition_balance__sum"]
            or 0
        )

        return Response(
            {
                "total_students": total_students,
                "active_students": active_students,
                "active_dorm_students": active_dorm,
                "total_balance": float(total_balance),
            }
        )

    @action(detail=False, methods=["get"])
    def dropouts(self, request):
        """Get all dropout students"""
        dropouts = Student.objects.filter(status="Drop-out")
        serializer = StudentSerializer(dropouts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def inactive(self, request):
        """Get all inactive students"""
        inactive = Student.objects.filter(status="Inactive")
        serializer = StudentSerializer(inactive, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def transferred(self, request):
        """Get all transferred students"""
        transferred = Student.objects.filter(status="Transferred")
        serializer = StudentSerializer(transferred, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def dropouts_inactive(self, request):
        """Get all dropout, inactive and transferred students"""
        students = Student.objects.filter(
            status__in=["Drop-out", "Inactive", "Transferred"]
        )
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_dropout(self, request, pk=None):
        """Mark a student as dropout"""
        from django.utils import timezone
        from dropouts.models import Dropout as DropoutRecord

        student = self.get_object()
        reason = request.data.get("reason", "")

        student.status = "Drop-out"
        student.save()

        # Keep the Dropout record in sync with Student.status. Previously only
        # the status flag was set, so /api/dropouts/ and the dropout statistics
        # endpoint stayed empty and the two sources of truth disagreed.
        DropoutRecord.objects.update_or_create(
            student=student,
            defaults={
                "dropout_date": request.data.get("dropout_date")
                or timezone.now().date(),
                # Reinstatement keeps the row for history rather than deleting
                # it, and Dropout.student is OneToOne, so a student who leaves
                # again reuses the same row. Without resetting these the record
                # would stay 'reinstated': invisible in the dropouts list and
                # still promotable, while Student.status said 'Drop-out'.
                "status": "confirmed",
                "reinstated_at": None,
                # Capture where they were at the time, before any later edits.
                "last_grade_level": (
                    request.data.get("last_grade_level")
                    or student.current_grade_level
                    or None
                ),
                "last_section": request.data.get("last_section") or student.section or None,
                "reason": reason,
                "notes": request.data.get("notes") or None,
                "recorded_by": request.user.get_full_name()
                or request.user.username,
            },
        )

        return Response(
            {
                "success": True,
                "message": f"Student {student.lrn} marked as dropout",
                "reason": reason,
            }
        )

    @action(detail=True, methods=["post"])
    def reinstate(self, request, pk=None):
        """Reinstate a dropout student"""
        from django.utils import timezone as _tz
        from dropouts.models import Dropout as DropoutRecord

        student = self.get_object()

        student.status = "Active"
        student.save()

        # Flag the record as reinstated instead of deleting it. Deleting threw
        # away the dropout history and made it impossible to tell a former
        # dropout from a current one. A reinstated record no longer blocks
        # promotion.
        DropoutRecord.objects.filter(student=student).update(
            status="reinstated", reinstated_at=_tz.now()
        )

        return Response(
            {
                "success": True,
                "message": f"Student {student.lrn} reinstated successfully",
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_assign_section(self, request):
        """Bulk-assign section (and track/strand) to a cohort of students.

        Two-phase by design: call with `dry_run: true` to get the preview and
        per-student verdicts, then repeat with the chosen ids to apply. The apply
        runs in a single transaction so a partial bulk assignment cannot happen.
        """
        from django.db import transaction
        from django.utils import timezone
        from tracks.models import Section as SectionModel

        level_type = (request.data.get("level_type") or "").strip()
        grade_level = (request.data.get("grade_level") or "").strip()
        track = (request.data.get("track") or "").strip()
        strand = (request.data.get("strand") or "").strip()
        # Back-compat: older callers sent one combined track_strand string.
        track_strand = (request.data.get("track_strand") or "").strip()
        if not strand and not track:
            strand = track_strand
        target_section = (request.data.get("section") or "").strip()
        include_dropouts = str(request.data.get("include_dropouts", "")).lower() in (
            "true",
            "1",
            "yes",
        )
        dry_run = str(request.data.get("dry_run", "true")).lower() in ("true", "1", "yes")

        if not level_type or not grade_level or not (track or strand):
            return Response(
                {
                    "error": "level_type, grade_level and a track/strand are all required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- build the cohort ---
        qs = Student.objects.all()
        qs = qs.filter(level_type=level_type)

        # Grade can be given as a human label ("Grade 11") or the raw column
        # value ("11" / "1" / "2"). Accept both, and fall back to
        # current_grade_level so a student whose raw column drifted still
        # matches the label shown in the UI.
        raw = grade_level
        m = __import__("re").match(r"(\d+)", raw)
        grade_q = Q()
        if m:
            num = m.group(1)
            grade_q = Q(shs_grade=num, college_year=num)
            grade_q |= Q(current_grade_level__iexact=raw)
        else:
            grade_q = Q(current_grade_level__iexact=raw)
        qs = qs.filter(grade_q)

        # Track and Strand are separate concepts: pick the track, then the
        # strand under it. Student.track_strand is unreliable (it holds a
        # strand code for some rows, a display name for others, and nothing
        # for a few), so prefer the strand FK and fall back to matching the
        # stored string against strand code AND name.
        from tracks.models import Strand as StrandModel, Track as TrackModel

        strand_q = Q()
        strand_obj = None

        if strand:
            # Accept a strand id, its code, or its name.
            if str(strand).isdigit():
                strand_obj = StrandModel.objects.filter(pk=int(strand)).first()
            if strand_obj is None:
                strand_obj = StrandModel.objects.filter(code__iexact=strand).first()
            if strand_obj is None:
                strand_obj = StrandModel.objects.filter(name__iexact=strand).first()

            if strand_obj is not None:
                if track:
                    # The strand must belong to the chosen track.
                    track_obj = TrackModel.objects.filter(
                        Q(pk=int(track)) | Q(code__iexact=track) | Q(name__iexact=track)
                    ).first() if str(track).isdigit() else (
                        TrackModel.objects.filter(
                            Q(code__iexact=track) | Q(name__iexact=track)
                        ).first()
                    )
                    if track_obj is None or strand_obj.track_id != track_obj.pk:
                        return Response(
                            {"error": f"Strand '{strand}' does not belong to track '{track}'."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                strand_q = Q(strand=strand_obj.pk)
                strand_q |= Q(track_strand__iexact=strand_obj.name)
                strand_q |= Q(track_strand__iexact=strand_obj.code)
            else:
                strand_q = Q(strand__name__iexact=strand) | Q(track_strand__iexact=strand)

        if track:
            if str(track).isdigit():
                track_q = Q(strand__track_id=int(track))
            else:
                track_q = (
                    Q(strand__track__code__iexact=track)
                    | Q(strand__track__name__iexact=track)
                    | Q(track_strand__iexact=track)
                )
            strand_q = strand_q & track_q if strand else track_q

        if strand_q:
            qs = qs.filter(strand_q)

        if not include_dropouts:
            qs = qs.exclude(status__in=["Drop-out", "Inactive", "Transferred"])

        candidates = list(
            qs.order_by("last_name", "first_name").values(
                "id",
                "first_name",
                "last_name",
                "lrn",
                "section",
                "track_strand",
                "status",
                "current_grade_level",
            )
        )

        # --- dry run: report only, no writes ---
        if dry_run:
            if not target_section:
                return Response(
                    {
                        "error": "section is required to build the preview",
                        "count": len(candidates),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            moving, staying = [], []
            for s in candidates:
                row = dict(s)
                row["already_in_target"] = (s["section"] or "").strip() == target_section
                (staying if row["already_in_target"] else moving).append(row)
            return Response(
                {
                    "dry_run": True,
                    "count": len(candidates),
                    "moving": moving,
                    "staying": staying,
                    "excluded_dropouts": (
                        Student.objects.filter(
                            level_type=level_type, status__in=["Drop-out", "Inactive", "Transferred"]
                        ).count()
                    ),
                }
            )

        # --- apply ---
        if not target_section:
            return Response(
                {"error": "section is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ids = request.data.get("student_ids")
        if ids is None:
            ids = [s["id"] for s in candidates]
        else:
            try:
                ids = [int(i) for i in ids]
            except (TypeError, ValueError):
                return Response(
                    {"error": "student_ids must be a list of integers"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # The section must already exist, otherwise StudentsPage (which groups
        # by section name) will not find it. Compare case-insensitively.
        known = set(
            SectionModel.objects.values_list("name", flat=True).distinct()
        )
        known_lower = {str(n).strip().lower() for n in known}
        if target_section.strip().lower() not in known_lower:
            return Response(
                {
                    "error": f"Section '{target_section}' does not exist. Create it first.",
                    "known_sections": sorted(str(n) for n in known),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        actor = (
            request.user.get_full_name() or request.user.username
            if request.user and request.user.is_authenticated
            else "unknown"
        )
        now = timezone.now()
        # What to write into the free-text Student.track_strand column. Prefer
        # the strand display name, then its code, then whatever was selected.
        # (Student.strand FK stays untouched unless an explicit strand was given.)
        strand_label = ""
        if strand:
            strand_label = (
                (strand_obj.name if strand_obj is not None else strand) or ""
            ).strip()
        elif track:
            strand_label = track
        # Rows whose stored value already equals the strand code should be
        # considered unchanged, so compare against both forms.
        acceptable_labels = {strand_label}
        if strand_obj is not None:
            acceptable_labels.update({strand_obj.name, strand_obj.code})

        # Only touch students in the cohort, so a crafted id list cannot reach
        # students outside the selected track/grade.
        scoped = qs.filter(id__in=ids)

        with transaction.atomic():
            updated = 0
            for student in scoped:
                # Skip no-op writes so already-correct rows are not churned.
                if (
                    (student.section or "").strip() == target_section
                    and (student.track_strand or "").strip() in acceptable_labels
                    and (not strand or student.strand_id == getattr(strand_obj, "pk", None) or student.strand_id)
                ):
                    continue
                student.section = target_section
                student.track_strand = strand_label
                if strand_obj is not None:
                    student.strand = strand_obj
                student.section_assigned_by = actor
                student.section_assigned_at = now
                student.save(
                    update_fields=[
                        "section",
                        "track_strand",
                        "strand",
                        "section_assigned_by",
                        "section_assigned_at",
                    ]
                )
                updated += 1

        return Response(
            {
                "success": True,
                "dry_run": False,
                "requested": len(ids),
                "updated": updated,
                "skipped_no_change": len(ids) - updated,
                "section": target_section,
                "track": track,
                "strand": strand_label,
                "assigned_by": actor,
            }
        )

    @action(detail=False, methods=["get"])
    def settlement_context(self, request):
        """Everything the cashier settlement panel needs for one student.

        Returns the student record plus their outstanding charges and balances
        so the left column renders from a single request instead of several.
        """
        from payments.models import StudentCharge as Charge

        try:
            student_id = int(request.query_params.get("student_id", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "student_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student = get_object_or_404(Student, id=student_id)

        charges = []
        item_total = 0
        for c in Charge.objects.filter(student=student).exclude(status="paid").order_by("id"):
            total = float(c.unit_price or 0) * int(c.qty or 1)
            balance = total - float(c.amount_paid or 0)
            if balance <= 0:
                continue
            item_total += balance
            charges.append({
                "id": c.id,
                "item_name": c.item_name,
                "description": c.notes or "",
                "unit_price": float(c.unit_price or 0),
                "qty": int(c.qty or 1),
                "amount_paid": float(c.amount_paid or 0),
                "balance": round(balance, 2),
                "status": c.status,
                "source": c.source,
            })

        tuition_balance = float(student.tuition_balance or 0)

        # The cashier settles tuition through the tuition endpoint, which takes
        # the running total to bring the account up to rather than the amount
        # taken now. It needs the fee and what has already been paid, so both
        # are published here. paid is summed from the payment rows rather than
        # read off Student.tuition_balance, which is a denormalised cache and
        # can drift from the rows that Revenue and the SOA actually read.
        from django.db.models import Sum as _Sum
        tuition_paid = float(
            TuitionPayment.objects.filter(student=student)
            .aggregate(_s=_Sum("amount"))["_s"] or 0
        )
        tuition_fee = float(student.custom_tuition_fee or 0) or round(tuition_paid + tuition_balance, 2)

        # The tuition figure the cashier sees must come from the same rows
        # Revenue and the SOA read. When a fee is configured the due amount is
        # fee minus what the rows say has been paid; the cache is trusted only
        # when no fee is set, in which case fee - paid collapses to it anyway.
        # Returning the raw cache here is what made the Tuition line read
        # 0.00 for students whose balance was never written back to.
        if student.custom_tuition_fee:
            tuition_due = round(max(tuition_fee - tuition_paid, 0.0), 2)
        else:
            tuition_due = tuition_balance
        # Tuition source charges are excluded from the item total because
        # tuition_due already accounts for money taken.
        outstanding = round(item_total + tuition_due, 2)

        # Per-quarter tuition breakdown, so the cashier can show what the fee
        # is made of without opening another page. OneToOne, so it is simply
        # absent for students who have no breakdown row yet.
        breakdown_payload = None
        try:
            bd = student.tuition_breakdown
            breakdown_payload = {
                "academic_year": bd.academic_year,
                "quarters": [
                    {"label": "1st Quarter", "amount": float(bd.first_quarter or 0)},
                    {"label": "2nd Quarter", "amount": float(bd.second_quarter or 0)},
                    {"label": "3rd Quarter", "amount": float(bd.third_quarter or 0)},
                    {"label": "4th Quarter", "amount": float(bd.fourth_quarter or 0)},
                ],
                "total": float(bd.total),
            }
        except ObjectDoesNotExist:
            pass

        serializer = StudentSerializer(student, context={"request": request})
        return Response({
            "student": serializer.data,
            "unpaid_charges": charges,
            "tuition_breakdown": breakdown_payload,
            "totals": {
                "item_total": round(item_total, 2),
                # Authoritative tuition due (fee - paid from the rows), not the
                # raw cache - see the comment above.
                "tuition_balance": tuition_due,
                "outstanding": outstanding,
                "tuition_fee": round(tuition_fee, 2),
                "tuition_paid": round(tuition_paid, 2),
            },
        })

    @action(detail=False, methods=["get"])
    def promotion_preview(self, request):
        """Preview students eligible for promotion"""
        promote_type = request.query_params.get("type", "all")

        # "Already graduated" must be judged by a real StudentGraduation
        # record, not by Student.enrollment_status. Bulk promote sets that
        # string to "Graduated" without creating a graduation record, which
        # hid every Grade 12 student from this page even though they are
        # still sitting in Grade 12.
        from graduation.models import StudentGraduation as StudentGraduationRec
        not_graduated = ~Q(
            id__in=StudentGraduationRec.objects.values("student_id")
        )

        # Dropouts are never promoted. Judged by BOTH the Dropout record and
        # Student.status, because the two were allowed to drift apart (a
        # student could carry a dropout record while status stayed "Active").
        not_dropped_out = (
            ~Q(dropout_record__status="confirmed")
            & ~Q(status__iexact="Drop-out")
        )
        # Dropouts are stored as Inactive so they remain visible on the student
        # list, so status alone is not enough - the Dropout record is the
        # authority. Only Active students are ever promotable.
        not_inactive = ~Q(status__in=["Inactive", "Drop-out", "Transferred"])

        preview = {
            "shs_grade_11": [],
            "shs_grade_12": [],
            "bundled_year_1": [],
            "bundled_year_2": [],
        }
        excluded_dropouts = {
            "shs_grade_11": [],
            "shs_grade_12": [],
            "bundled_year_1": [],
            "bundled_year_2": [],
        }
        fields = ("id", "first_name", "last_name", "lrn", "section", "track_strand")
        graduated_qs = StudentGraduationRec.objects.values("student_id")

        if promote_type in ["shs", "all"]:
            grade_11 = Student.objects.filter(
                Q(level_type="SHS", shs_grade="11") |
                Q(current_grade_level="Grade 11"),
                not_graduated,
                not_dropped_out,
                not_inactive,
            ).values(*fields)
            preview["shs_grade_11"] = list(grade_11)
            excluded_dropouts["shs_grade_11"] = list(
                Student.objects.filter(
                    Q(level_type="SHS", shs_grade="11") |
                    Q(current_grade_level="Grade 11"),
                    not_graduated,
                ).exclude(id__in=[s["id"] for s in preview["shs_grade_11"]])
                .values(*fields)
            )

            grade_12 = Student.objects.filter(
                Q(level_type="SHS", shs_grade="12") |
                Q(current_grade_level="Grade 12"),
                not_graduated,
                not_dropped_out,
                not_inactive,
            ).values(*fields)
            preview["shs_grade_12"] = list(grade_12)
            excluded_dropouts["shs_grade_12"] = list(
                Student.objects.filter(
                    Q(level_type="SHS", shs_grade="12") |
                    Q(current_grade_level="Grade 12"),
                    not_graduated,
                ).exclude(id__in=[s["id"] for s in preview["shs_grade_12"]])
                .values(*fields)
            )

        if promote_type in ["bundled", "all"]:
            year_1 = Student.objects.filter(
                Q(level_type="BUN", college_year="1") |
                Q(current_grade_level="1st Year Bundled") |
                Q(current_grade_level="1st Year Tesda Accredited"),
                not_graduated,
                not_dropped_out,
                not_inactive,
            ).values(*fields)
            preview["bundled_year_1"] = list(year_1)
            excluded_dropouts["bundled_year_1"] = list(
                Student.objects.filter(
                    Q(level_type="BUN", college_year="1") |
                    Q(current_grade_level="1st Year Bundled") |
                    Q(current_grade_level="1st Year Tesda Accredited"),
                    not_graduated,
                ).exclude(id__in=[s["id"] for s in preview["bundled_year_1"]])
                .values(*fields)
            )

            year_2 = Student.objects.filter(
                Q(level_type="BUN", college_year="2") |
                Q(current_grade_level="2nd Year Bundled") |
                Q(current_grade_level="2nd Year Tesda Accredited"),
                not_graduated,
                not_dropped_out,
                not_inactive,
            ).values(*fields)
            preview["bundled_year_2"] = list(year_2)
            excluded_dropouts["bundled_year_2"] = list(
                Student.objects.filter(
                    Q(level_type="BUN", college_year="2") |
                    Q(current_grade_level="2nd Year Bundled") |
                    Q(current_grade_level="2nd Year Tesda Accredited"),
                    not_graduated,
                ).exclude(id__in=[s["id"] for s in preview["bundled_year_2"]])
                .values(*fields)
            )

        # Group each cohort by section so the page can drill into sections
        # instead of offering only an all-or-nothing cohort action.
        by_section = {}
        for cohort, students in preview.items():
            grouped = {}
            for student in students:
                name = (student.get("section") or "").strip() or "Unassigned"
                grouped.setdefault(name, []).append(student)
            by_section[cohort] = [
                {"section": name, "count": len(rows), "students": rows}
                for name, rows in sorted(grouped.items())
            ]

        return Response(
            {
                "preview": preview,
                "by_section": by_section,
                "excluded_dropouts": excluded_dropouts,
                # Students who already ran through promotion. Surfaced so the
                # page can explain an empty list instead of looking broken.
                "already_promoted": {
                    "shs_grade_12": list(
                        Student.objects.filter(
                            Q(level_type="SHS", shs_grade="12")
                            | Q(current_grade_level="Grade 12"),
                            id__in=graduated_qs,
                        ).values(
                            "id", "first_name", "last_name", "lrn", "section",
                            "track_strand", "enrollment_status", "current_grade_level",
                        )
                    ),
                    "bundled_year_2": list(
                        Student.objects.filter(
                            Q(level_type="BUN", college_year="2")
                            | Q(current_grade_level__icontains="2nd Year"),
                            id__in=graduated_qs,
                        ).values(
                            "id", "first_name", "last_name", "lrn", "section",
                            "track_strand", "enrollment_status", "current_grade_level",
                        )
                    ),
                },
                "counts": {
                    "shs_grade_11_to_12": len(preview["shs_grade_11"]),
                    "shs_grade_12_to_graduate": len(preview["shs_grade_12"]),
                    "bundled_year_1_to_2": len(preview["bundled_year_1"]),
                    "bundled_year_2_to_graduate": len(preview["bundled_year_2"]),
                },
            }
        )

    @action(detail=False, methods=["post"])
    def promote_students(self, request):
        """Promote students to next year level"""
        from graduation.models import StudentGraduation as StudentGraduationRec

        promote_type = request.data.get("type", "all")
        promoted_count = 0
        graduated_count = 0

        # Same rule as promotion_preview: graduation is judged by an actual
        # StudentGraduation record, not the enrollment_status string. Using the
        # string made Promote a silent no-op for anyone bulk-promoted before.
        not_graduated = ~Q(
            id__in=StudentGraduationRec.objects.values("student_id")
        )

        # Never promote a dropout - judged by both the Dropout record and
        # status, since those two can disagree.
        not_dropped_out = (
            ~Q(dropout_record__status="confirmed")
            & ~Q(status__iexact="Drop-out")
        )
        # Only Active students are ever promotable (see preview for why).
        not_inactive = ~Q(status__in=["Inactive", "Drop-out", "Transferred"])

        # Optional section scope, so the page can promote one section at a time
        # instead of only a whole cohort. Empty/absent means the whole cohort.
        section = (request.data.get("section") or "").strip()

        def scoped(qs):
            if section:
                return qs.filter(section=section)
            return qs

        skipped_dropouts = 0

        # Dropout/inactive exclusion, counted on the unscoped-by-status query
        # so the UI can explain a no-op ("2 skipped (dropout)") instead of
        # silently promoting nothing. Only a CONFIRMED dropout blocks; a
        # reinstated record is history and the student is promotable again.
        excluded_q = (
            Q(dropout_record__status="confirmed")
            | Q(status__in=["Inactive", "Drop-out", "Transferred"])
        )

        def prepare(qs):
            """Count excluded, then return the promotable queryset."""
            nonlocal skipped_dropouts
            base = qs.filter(not_graduated)
            skipped_dropouts += base.filter(excluded_q).distinct().count()
            return base.filter(not_dropped_out, not_inactive)

        try:
            if promote_type in ["shs", "all"]:
                grade_11_students = prepare(scoped(Student.objects.filter(
                    Q(level_type="SHS", shs_grade="11") |
                    Q(current_grade_level="Grade 11"),
                )))

                for student in grade_11_students:
                    student.level_type = "SHS"
                    student.shs_grade = "12"
                    student.current_grade_level = "Grade 12"
                    student.enrollment_status = "Continuing"

                    try:
                        # No fee table: carry the student's own fee forward and
                        # recompute the balance from actual payments.
                        if student.custom_tuition_fee:
                            student.tuition_balance = max(
                                Decimal("0"),
                                Decimal(str(student.custom_tuition_fee))
                                - sum(
                                    Decimal(str(p.amount or 0))
                                    for p in student.tuition_payments.all()
                                ),
                            )
                    except Exception as e:
                        logger.exception(
                            "Error updating tuition on promotion "
                            "student_id=%s exc=%s",
                            getattr(student, "id", None),
                            type(e).__name__,
                        )

                    student.save()
                    promoted_count += 1

                grade_12_students = prepare(scoped(Student.objects.filter(
                    Q(level_type="SHS", shs_grade="12") |
                    Q(current_grade_level="Grade 12"),
                )))

                for student in grade_12_students:
                    student.level_type = "SHS"
                    student.shs_grade = "12"
                    student.enrollment_status = "Graduated"
                    student.save()
                    graduated_count += 1

            if promote_type in ["bundled", "all"]:
                year_1_students = prepare(scoped(Student.objects.filter(
                    Q(level_type="BUN", college_year="1") |
                    Q(current_grade_level="1st Year Bundled") |
                    Q(current_grade_level="1st Year Tesda Accredited"),
                )))

                for student in year_1_students:
                    student.level_type = "BUN"
                    student.college_year = "2"
                    student.current_grade_level = "2nd Year Bundled"
                    student.enrollment_status = "Continuing"

                    try:
                        # No fee table: carry the student's own fee forward.
                        if student.custom_tuition_fee:
                            student.tuition_balance = max(
                                Decimal("0"),
                                Decimal(str(student.custom_tuition_fee))
                                - sum(
                                    Decimal(str(p.amount or 0))
                                    for p in student.tuition_payments.all()
                                ),
                            )
                    except Exception as e:
                        logger.exception(
                            "Error updating tuition on bundled promotion "
                            "student_id=%s exc=%s",
                            getattr(student, "id", None),
                            type(e).__name__,
                        )

                    student.save()
                    promoted_count += 1

                year_2_students = prepare(scoped(Student.objects.filter(
                    Q(level_type="BUN", college_year="2") |
                    Q(current_grade_level="2nd Year Bundled") |
                    Q(current_grade_level="2nd Year Tesda Accredited"),
                )))

                for student in year_2_students:
                    student.level_type = "BUN"
                    student.college_year = "2"
                    student.enrollment_status = "Graduated"
                    student.current_grade_level = "Graduated"
                    student.save()
                    graduated_count += 1

            return Response(
                {
                    "success": True,
                    "message": f"Successfully promoted {promoted_count} students and graduated {graduated_count} students",
                    "promoted_count": promoted_count,
                    "graduated_count": graduated_count,
                    # Surfaced so the UI can explain a no-op instead of
                    # silently promoting nothing.
                    "skipped_dropouts": skipped_dropouts,
                    "section": section or None,
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def bulk_upload(self, request):
        """Upload students from Excel file"""

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"success": False, "error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not file.name.endswith((".xlsx", ".xls")):
            return Response(
                {
                    "success": False,
                    "error": "Please upload an Excel file (.xlsx or .xls)",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Load the workbook
            if file.name.endswith(".xlsx"):
                workbook = load_workbook(io.BytesIO(file.read()))
            else:
                return Response(
                    {"success": False, "error": "Only .xlsx files are supported"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Try to get the "Student Data Enrollment" sheet, fallback to active sheet
            if "Student Data Enrollment" in workbook.sheetnames:
                sheet = workbook["Student Data Enrollment"]
            else:
                sheet = workbook.active

            # Get headers from first row
            headers = []
            for cell in sheet[1]:
                if cell.value:
                    headers.append(str(cell.value).strip().lower())

            if not headers:
                return Response(
                    {"success": False, "error": "No headers found in the first row"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            created_count = 0
            updated_count = 0
            errors = []
            skipped_count = 0

            for row_num, row in enumerate(
                sheet.iter_rows(min_row=2, values_only=False), start=2
            ):
                try:
                    row_data = {}
                    for idx, header in enumerate(headers):
                        if idx < len(row):
                            cell_value = row[idx].value
                            row_data[header] = (
                                cell_value if cell_value is not None else ""
                            )

                    # Extract fields - support multiple header variations
                    # Debug: Print first row's data to help diagnose issues
                    if row_num == 2 and not errors:
                        logger.debug(
                            "import row 2 header sample: %s", list(row_data.keys())[:5]
                        )

                    lrn = str(
                        row_data.get("lrn", "") or row_data.get("student_id", "")
                    ).strip()
                    first_name = str(
                        row_data.get("firstname", "")
                        or row_data.get("first_name", "")
                        or row_data.get("first name", "")
                    ).strip()
                    last_name = str(
                        row_data.get("lastname", "")
                        or row_data.get("last_name", "")
                        or row_data.get("last name", "")
                    ).strip()
                    middle_name = str(
                        row_data.get("middle", "")
                        or row_data.get("middlename", "")
                        or row_data.get("middle_name", "")
                        or row_data.get("middle name", "")
                    ).strip()
                    grade_level = str(
                        row_data.get("gradelevel", "")
                        or row_data.get("grade_level", "")
                        or row_data.get("grade/year level", "")
                        or row_data.get("grade", "")
                    ).strip()
                    level_type = (
                        str(
                            row_data.get("leveltype", "")
                            or row_data.get("level_type", "")
                            or row_data.get("level type (shs/col/bun)", "")
                            or row_data.get("level", "")
                        )
                        .strip()
                        .upper()
                    )
                    enrollment_status = str(
                        row_data.get("status", "")
                        or row_data.get("enrollment_status", "")
                        or row_data.get("enrollment status", "")
                        or "New"
                    ).strip()
                    track_strand = str(
                        row_data.get("track_strand", "")
                        or row_data.get("track/course code", "")
                        or row_data.get("strand", "")
                        or row_data.get("track", "")
                    ).strip()
                    section = str(row_data.get("section", "")).strip()
                    tuition = str(
                        row_data.get("tuition", "")
                        or row_data.get("tuition_balance", "")
                        or row_data.get("tuition fee (grade 11 & 12 only)", "")
                    ).strip()

                    # Debug: Print extracted values for first row
                    if row_num == 2 and not errors:
                        logger.debug("import row 2 produced %d fields", len(row_data))

                    # Skip empty rows
                    if not lrn and not last_name and not first_name:
                        skipped_count += 1
                        continue

                    # Validate required fields
                    if not lrn or not last_name or not first_name:
                        errors.append(
                            f"Row {row_num}: Missing required fields (LRN='{lrn}', FirstName='{first_name}', LastName='{last_name}')"
                        )
                        continue

                    # Validate level type
                    if level_type and level_type not in ["SHS", "COL", "BUN"]:
                        errors.append(
                            f"Row {row_num}: Invalid level type '{level_type}'"
                        )
                        continue

                    if not level_type:
                        level_type = "SHS"  # Default

                    # Validate enrollment status
                    valid_statuses = ["New", "Continuing", "Transferee", "ALS Graduate"]
                    if enrollment_status not in valid_statuses:
                        enrollment_status = "New"

                    # Tuition: only ever set from an explicit Tuition column.
                    # No auto-calculation from status - the fee structure is not
                    # inferred here, tuition is assigned manually per student
                    # afterwards. Anything unparseable leaves the balance at 0.
                    tuition_balance = 0
                    if tuition:
                        try:
                            tuition_balance = float(tuition)
                        except (ValueError, TypeError):
                            tuition_balance = 0

                    # Determine SHS grade or bundled year (only 1st/2nd Year)
                    shs_grade = None
                    college_year = None
                    if level_type == "SHS":
                        if "12" in str(grade_level):
                            shs_grade = "12"
                        else:
                            shs_grade = "11"
                    elif level_type in ("BUN", "COL"):
                        if "2" in str(grade_level):
                            college_year = "2"
                        else:
                            college_year = "1"

                    # Create or update student
                    student, created = Student.objects.update_or_create(
                        lrn=lrn,
                        defaults={
                            "first_name": first_name,
                            "last_name": last_name,
                            "middle_name": middle_name,
                            "level_type": level_type,
                            "enrollment_status": enrollment_status,
                            "tuition_balance": tuition_balance,
                            "shs_grade": shs_grade,
                            "college_year": college_year,
                            "track_strand": track_strand if track_strand else None,
                            "section": section if section else None,
                            "current_grade_level": grade_level if grade_level else None,
                        },
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

            return Response(
                {
                    "success": True,
                    "message": f"Successfully processed {created_count + updated_count} students",
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "skipped_count": skipped_count,
                    "total_rows_processed": row_num - 1,
                    "errors": errors[:20] if errors else [],  # Limit errors to first 20
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def by_section(self, request):
        """Get students by section"""
        section = request.query_params.get("section")
        if not section:
            return Response(
                {"error": "section parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        students = Student.objects.filter(section=section).order_by(
            "last_name", "first_name"
        )
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_grade(self, request):
        """Get students by grade level (supports SHS grades and college years)"""
        grade = request.query_params.get("grade")
        level_type = request.query_params.get("level_type")

        if not grade:
            return Response(
                {"error": "grade parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Student.objects.all()

        if level_type == "SHS":
            queryset = queryset.filter(level_type="SHS", shs_grade=grade)
        elif level_type == "BUN":
            queryset = queryset.filter(level_type="BUN", college_year=grade)
        elif level_type == "COL":
            queryset = queryset.filter(level_type="COL", college_year=grade)
        else:
            # Try to match either field if level_type not specified
            queryset = queryset.filter(Q(shs_grade=grade) | Q(college_year=grade))

        students = queryset.order_by("last_name", "first_name")
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def test_upload(self, request):
        """Test endpoint to debug Excel uploads — DEBUG only."""
        if not settings.DEBUG:
            return Response(
                {"error": "Not available"},
                status=status.HTTP_403_FORBIDDEN,
            )

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            workbook = load_workbook(io.BytesIO(file.read()))

            # Get sheet info
            sheet_names = workbook.sheetnames
            if "Student Data Enrollment" in sheet_names:
                sheet = workbook["Student Data Enrollment"]
            else:
                sheet = workbook.active

            # Get headers
            headers = []
            for cell in sheet[1]:
                if cell.value:
                    headers.append(str(cell.value).strip().lower())

            # Get first data row
            first_row = list(sheet.iter_rows(min_row=2, max_row=2, values_only=True))[0]

            return Response(
                {
                    "sheet_names": sheet_names,
                    "active_sheet": sheet.title,
                    "headers": headers,
                    "first_row_data": first_row,
                    "total_rows": sheet.max_row,
                }
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudentDocumentViewSet(viewsets.ModelViewSet):
    """Document management"""

    queryset = StudentDocument.objects.all()
    serializer_class = StudentDocumentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """Verify a document"""
        document = self.get_object()
        document.is_verified = True
        document.verified_by = request.user
        document.verified_at = datetime.now()
        document.save()
        return Response(
            {"status": "verified", "message": "Document verified successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def unverify(self, request, pk=None):
        """Unverify a document"""
        document = self.get_object()
        document.is_verified = False
        document.verified_by = None
        document.verified_at = None
        document.save()
        return Response(
            {"status": "unverified", "message": "Document unverified successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get all unverified documents"""
        documents = StudentDocument.objects.filter(is_verified=False)
        serializer = StudentDocumentSerializer(documents, many=True)
        return Response(serializer.data)


class DormBuildingViewSet(viewsets.ModelViewSet):
    """Dorm building management"""

    queryset = (
        DormBuilding.objects.filter(is_active=True)
        if hasattr(DormBuilding, "is_active")
        else DormBuilding.objects.all()
    )
    serializer_class = DormBuildingSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def rooms(self, request, pk=None):
        """Get all rooms in building"""
        building = self.get_object()
        rooms_query = building.rooms.all()
        if hasattr(DormRoom, "is_active"):
            rooms_query = rooms_query.filter(is_active=True)
        serializer = DormRoomSerializer(rooms_query, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get dorm building statistics"""
        building_query = DormBuilding.objects.all()
        if hasattr(DormBuilding, "is_active"):
            building_query = building_query.filter(is_active=True)

        total_buildings = building_query.count()

        room_query = DormRoom.objects.all()
        if hasattr(DormRoom, "is_active"):
            room_query = room_query.filter(is_active=True)

        total_rooms = room_query.count()
        total_students = DormAssignment.objects.filter(status="Active").count()

        return Response(
            {
                "total_buildings": total_buildings,
                "total_rooms": total_rooms,
                "active_assignments": total_students,
            }
        )


class DormRoomViewSet(viewsets.ModelViewSet):
    """Dorm room management"""

    queryset = (
        DormRoom.objects.filter(is_active=True)
        if hasattr(DormRoom, "is_active")
        else DormRoom.objects.all()
    )
    serializer_class = DormRoomSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def available(self, request):
        """Get available rooms"""
        rooms_query = DormRoom.objects.all()
        if hasattr(DormRoom, "is_active"):
            rooms_query = rooms_query.filter(is_active=True)

        available_list = []
        for room in rooms_query:
            occupants = DormAssignment.objects.filter(
                room=room, status="Active"
            ).count()
            if occupants < room.capacity:
                available_list.append(room)

        serializer = DormRoomSerializer(available_list, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_building(self, request):
        """Get rooms filtered by building"""
        building_id = request.query_params.get("building_id")

        if not building_id:
            return Response(
                {"error": "building_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        rooms_query = DormRoom.objects.filter(building_id=building_id)
        if hasattr(DormRoom, "is_active"):
            rooms_query = rooms_query.filter(is_active=True)

        serializer = DormRoomSerializer(rooms_query, many=True)
        return Response(serializer.data)


class DormAssignmentViewSet(viewsets.ModelViewSet):
    """Dorm assignment management"""

    queryset = DormAssignment.objects.all()
    serializer_class = DormAssignmentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get active assignments"""
        assignments = DormAssignment.objects.filter(status="Active")
        serializer = DormAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_student(self, request):
        """Get assignments by student"""
        student_id = request.query_params.get("student_id")

        if not student_id:
            return Response(
                {"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        assignments = DormAssignment.objects.filter(student_id=student_id)
        serializer = DormAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        """Terminate assignment"""
        assignment = self.get_object()
        assignment.date_ended = request.data.get("date_ended", datetime.now())
        assignment.status = "Terminated"
        assignment.save()

        return Response(
            {"status": "terminated", "message": "Assignment terminated successfully"},
            status=status.HTTP_200_OK,
        )


class DormPaymentViewSet(viewsets.ModelViewSet):
    """Dorm payment management"""

    queryset = DormPayment.objects.all()
    serializer_class = DormPaymentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def by_student(self, request):
        """Get payments by student"""
        student_id = request.query_params.get("student_id")

        if not student_id:
            return Response(
                {"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        payments = DormPayment.objects.filter(assignment__student_id=student_id)
        serializer = DormPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_month(self, request):
        """Get payments by month"""
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        if not month or not year:
            return Response(
                {"error": "month and year parameters required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payments = DormPayment.objects.filter(month_covered=month, year_covered=year)
        serializer = DormPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get payment statistics"""
        total_payments = DormPayment.objects.count()
        total_amount = DormPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0

        return Response(
            {"total_payments": total_payments, "total_amount": float(total_amount)}
        )


class ProductViewSet(viewsets.ModelViewSet):
    """Product CRUD operations"""

    # Ordered so DRF pagination is stable across pages.
    queryset = Product.objects.all().order_by("name")
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search products by name or barcode"""
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response(
                {"error": "q parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        products = Product.objects.filter(
            Q(name__icontains=query) | Q(barcode__icontains=query)
        ).order_by("name")

        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """Get products with low stock (stock <= reorder_level)"""
        threshold = request.query_params.get("threshold", 10)

        try:
            threshold = int(threshold)
        except ValueError:
            threshold = 10

        products = Product.objects.filter(stock__lte=threshold).order_by(
            "stock", "name"
        )

        serializer = self.get_serializer(products, many=True)
        return Response(
            {
                "count": products.count(),
                "threshold": threshold,
                "products": serializer.data,
            }
        )


class SaleViewSet(viewsets.ModelViewSet):
    """Sales management"""

    queryset = Sale.objects.all().order_by("-created_at")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return SaleCreateSerializer
        return SaleSerializer

    def get_queryset(self):
        queryset = (
            Sale.objects.all()
            .select_related("student")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        # Date filtering
        start_date = self.request.query_params.get("start")
        end_date = self.request.query_params.get("end")

        # Payment status filtering
        payment_status = self.request.query_params.get("payment_status")

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if payment_status:
            if payment_status == "pending":
                # Pending means partial or unpaid
                queryset = queryset.filter(payment_status__in=["partial", "unpaid"])
            else:
                queryset = queryset.filter(payment_status=payment_status)

        return queryset

    def create(self, request, *args, **kwargs):
        """Override create to return proper serialized sale"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sale = serializer.save()
        # Return using SaleSerializer for proper response
        response_serializer = SaleSerializer(sale)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_payment(self, request, pk=None):
        """Add a payment to an existing sale"""
        from decimal import Decimal

        sale = self.get_object()
        amount = request.data.get("amount")
        payment_method = request.data.get("payment_method", "cash")
        gcash_number = request.data.get("gcash_number", "")
        gcash_reference = request.data.get("gcash_reference", "")

        if not amount:
            return Response(
                {"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = Decimal(str(amount))
        except:
            return Response(
                {"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST
            )

        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than 0"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add payment to sale
        sale.amount_paid += amount
        sale.payment_method = payment_method
        if gcash_number:
            sale.gcash_number = gcash_number
        if gcash_reference:
            sale.gcash_reference = gcash_reference

        # Update payment status
        if sale.amount_paid >= sale.total:
            sale.payment_status = "paid"
        else:
            sale.payment_status = "partial"

        sale.save()

        return Response(SaleSerializer(sale).data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get all pending (partial or unpaid) sales"""
        queryset = Sale.objects.filter(
            payment_status__in=["partial", "unpaid"]
        ).order_by("-created_at")

        serializer = SaleSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get sales statistics"""
        total_sales = Sale.objects.count()
        total_revenue = Sale.objects.aggregate(Sum("total"))["total__sum"] or 0
        total_collected = (
            Sale.objects.aggregate(Sum("amount_paid"))["amount_paid__sum"] or 0
        )
        total_pending = Sale.objects.filter(
            payment_status__in=["partial", "unpaid"]
        ).aggregate(total=Sum("total"), paid=Sum("amount_paid"))
        pending_balance = float(total_pending["total"] or 0) - float(
            total_pending["paid"] or 0
        )
        pending_count = Sale.objects.filter(
            payment_status__in=["partial", "unpaid"]
        ).count()

        return Response(
            {
                "total_sales": total_sales,
                "total_revenue": float(total_revenue),
                "total_collected": float(total_collected),
                "pending_balance": pending_balance,
                "pending_count": pending_count,
            }
        )


class TuitionPaymentViewSet(viewsets.ModelViewSet):
    """Tuition payment management - handles payments and updates student balance"""

    serializer_class = TuitionPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TuitionPayment.objects.all().select_related("student").order_by("-date")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        return super().update(request, *args, **kwargs, partial=partial)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def _generate_reference_number(self):
        """Generate a unique reference number in format RCT-YYYYMMDD-####"""
        from django.db.models import Max as MaxFunc
        today_str = datetime.now().strftime("%Y%m%d")
        prefix = f"RCT-{today_str}-"
        last = TuitionPayment.objects.filter(
            reference_number__startswith=prefix
        ).aggregate(MaxFunc("reference_number"))["reference_number__max"]
        if last:
            seq = int(last.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    @action(detail=False, methods=["get"], url_path="records")
    def records(self, request):
        """Return aggregated tuition records per student"""
        from django.db.models import Sum, Max as MaxDate, Count

        students_with_data = Student.objects.filter(
            Q(custom_tuition_fee__gt=0) | Q(tuition_payments__isnull=False)
        ).distinct()

        agg = TuitionPayment.objects.values("student_id").annotate(
            amount_paid=Sum("amount"),
            payment_count=Count("id"),
            latest_payment_date=MaxDate("payment_date"),
        )

        payment_agg = {a["student_id"]: a for a in agg}

        records = []
        for student in students_with_data:
            pa = payment_agg.get(student.id, {})
            total_tuition = float(student.custom_tuition_fee or 0)
            amount_paid = float(pa.get("amount_paid") or 0)
            if total_tuition == 0:
                total_tuition = float(student.tuition_balance or 0) + amount_paid
            balance = total_tuition - amount_paid
# Overpayment must not be silently discarded. balance stays clamped at 0 so
            # existing consumers (settle flow, status) keep working, but the
            # credit is reported separately instead of vanishing.
            overpayment = 0
            if balance < 0:
                overpayment = round(-balance, 2)
                balance = 0

            status = "unpaid"
            if total_tuition > 0 and amount_paid >= total_tuition:
                status = "paid"
            elif amount_paid > 0:
                status = "partial"

            records.append({
                "student_id": student.id,
                "student_name": f"{student.first_name} {student.last_name}",
                "lrn": getattr(student, "lrn", "") or "",
                # Grade: prefer explicit current_grade_level; fall back to shs_grade
                # / college_year so older students (set before promotion) still show
                "grade": (
                    getattr(student, "current_grade_level", "")
                    or ("Grade " + student.shs_grade if getattr(student, "level_type", "") == "SHS" and student.shs_grade else "")
                    or ({"1": "1st Year", "2": "2nd Year"}.get(student.college_year, "") if getattr(student, "level_type", "") in ("BUN", "COL") else "")
                ),
                "section": getattr(student, "section", "") or "",
                "total_tuition": total_tuition,
                "amount_paid": amount_paid,
                "balance": balance,
                "overpayment": overpayment,
                "status": status,
                "payment_count": pa.get("payment_count", 0),
                "latest_payment_date": pa.get("latest_payment_date"),
                "latest_payment_method": None,
                "school_year": getattr(student, "school_year", "") or "",
            })

        records.sort(key=lambda r: r["student_name"].lower())

        page = self.paginate_queryset(records)
        if page is not None:
            serializer = TuitionRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TuitionRecordSerializer(records, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create a tuition payment and update student balance"""
        from django.db import transaction

        student_id = request.data.get("student_id")
        total_tuition = request.data.get("total_tuition")
        amount = request.data.get("amount")
        amount_paid = request.data.get("amount_paid")
        payment_method = request.data.get("payment_method", "Cash")
        payment_date = request.data.get("payment_date")
        description = request.data.get("description", "")
        notes = request.data.get("notes", "")
        gcash_number = request.data.get("gcash_number", "")
        gcash_reference = request.data.get("gcash_reference", "")
        check_number = request.data.get("check_number", "")
        check_bank = request.data.get("check_bank", "")
        school_year = request.data.get("school_year", "")

        if not student_id:
            return Response(
                {"error": "student_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                student = Student.objects.select_for_update().get(id=student_id)
            except Student.DoesNotExist:
                return Response(
                    {"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Handle initial tuition setup (from enrollment) vs payment
            if total_tuition is not None:
                # Initial tuition setup mode — set student's balance to total_tuition minus amount_paid
                try:
                    total = Decimal(str(total_tuition))
                    paid = Decimal(str(amount_paid or 0))
                except:
                    return Response(
                        {"error": "Invalid total_tuition or amount_paid"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if paid > total:
                    return Response(
                        {"error": "Amount paid cannot exceed total tuition"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # This branch serves two callers that mean different things by
                # `amount_paid`:
                #   * enrollment  - a brand-new fee, so `paid` IS this payment
                #   * settle/retop - an existing fee, and `paid` is the running
                #                    total to bring the account up to
                # Writing the cumulative figure straight into a new row
                # double-counted it: 8,500 already paid with 3,500 left,
                # settling "in full" added a row of 12,000 instead of 3,500,
                # so the account read 20,500 paid against a 12,000 fee and
                # showed a phantom 8,500 overpayment on the SOA.
                already_paid = TuitionPayment.objects.filter(
                    student=student
                ).aggregate(_s=Sum("amount"))["_s"] or Decimal("0")
                this_payment = (paid - already_paid) if already_paid > 0 else paid
                if this_payment < 0:
                    this_payment = Decimal("0")

                student.tuition_balance = total - paid
                student.custom_tuition_fee = total
                if school_year:
                    student.school_year = school_year
                student.save()

                # Create an initial payment record if amount_paid > 0
                if this_payment > 0:
                    method_map = {
                        "cash": "Cash", "gcash": "GCash", "check": "Bank Transfer",
                        "bank_transfer": "Bank Transfer", "card": "Credit/Debit Card",
                    }
                    method = method_map.get(payment_method.lower(), "Cash")
                    ref_number = self._generate_reference_number()
                    parsed_payment_date = None
                    if payment_date:
                        try:
                            parsed_payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
                        except:
                            pass
                    payment = TuitionPayment.objects.create(
                        student=student,
                        amount=this_payment,
                        method=method,
                        reference_number=ref_number,
                        payment_date=parsed_payment_date,
                        payment_method=payment_method,
                        notes=notes or None,
                        remarks=description or "Initial payment upon enrollment",
                    )
                else:
                    payment = None

                return Response(
                    {
                        "id": payment.id if payment else None,
                        "reference_number": payment.reference_number if payment else None,
                        "student_id": student.id,
                        "student_name": f"{student.first_name} {student.last_name}",
                        "lrn": student.lrn or "",
                        "grade": student.current_grade_level or "",
                        "total_tuition": float(total),
                        "amount_paid": float(paid),
                        "remaining_balance": float(student.tuition_balance),
                        "payment_date": payment_date,
                        "payment_method": payment_method,
                        "is_initial_setup": True,
                    },
                    status=status.HTTP_201_CREATED,
                )

            # Normal payment mode
            if not amount:
                return Response(
                    {"error": "amount is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                amount = Decimal(str(amount))
            except:
                return Response(
                    {"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Store previous balance for receipt
            previous_balance = float(student.tuition_balance)

            # Map frontend payment method to model choices
            method_map = {
                "cash": "Cash",
                "gcash": "GCash",
                "check": "Bank Transfer",
                "bank_transfer": "Bank Transfer",
                "card": "Credit/Debit Card",
            }
            method = method_map.get(payment_method.lower(), "Cash")

            # Build reference number
            reference_no = ""
            if gcash_reference:
                reference_no = gcash_reference
            elif check_number:
                reference_no = (
                    f"{check_bank} - {check_number}" if check_bank else check_number
                )

            ref_number = self._generate_reference_number()
            parsed_payment_date = None
            if payment_date:
                try:
                    parsed_payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
                except:
                    pass

            payment = TuitionPayment.objects.create(
                student=student,
                amount=amount,
                method=method,
                gcash_number=gcash_number or None,
                reference_no=reference_no or None,
                reference_number=ref_number,
                payment_date=parsed_payment_date,
                payment_method=payment_method,
                notes=notes or None,
                remarks=description or None,
            )

            # Update student's tuition balance (reduce by payment amount)
            student.tuition_balance = max(
                Decimal("0"), student.tuition_balance - amount
            )
            if school_year:
                student.school_year = school_year
            student.save()

            # Return response with payment details for receipt
            return Response(
                {
                    "id": payment.id,
                    "reference_number": payment.reference_number,
                    "student_id": student.id,
                    "student_name": f"{student.first_name} {student.last_name}",
                    "lrn": student.lrn or "",
                    "grade": student.current_grade_level or "",
                    "amount": float(amount),
                    "method": method,
                    "payment_method": payment_method,
                    "payment_date": payment_date,
                    "gcash_number": gcash_number,
                    "gcash_reference": gcash_reference,
                    "check_number": check_number,
                    "reference_no": reference_no,
                    "notes": notes,
                    "remarks": description,
                    "previous_balance": previous_balance,
                    "remaining_balance": float(student.tuition_balance),
                    "created_at": payment.created_at.isoformat(),
                    "date": payment.date.isoformat(),
                },
                status=status.HTTP_201_CREATED,
            )

    def update(self, request, *args, **kwargs):
        """Custom update — sync student.custom_tuition_fee and tuition_balance if total_tuition/amount_paid are passed"""
        from django.db import transaction

        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        total_tuition = request.data.get("total_tuition")
        amount_paid = request.data.get("amount_paid")
        student_id_override = request.data.get("student_id") or instance.student_id

        with transaction.atomic():
            try:
                student = Student.objects.select_for_update().get(id=student_id_override)
                from decimal import Decimal
                if total_tuition is not None:
                    try:
                        total_d = Decimal(str(total_tuition))
                        student.custom_tuition_fee = total_d
                        if amount_paid is not None:
                            try:
                                paid_d = Decimal(str(amount_paid))
                                student.tuition_balance = total_d - paid_d
                                if student.tuition_balance < 0:
                                    student.tuition_balance = Decimal("0")
                            except Exception:
                                pass
                        student.save()
                    except Exception:
                        pass
            except Student.DoesNotExist:
                pass

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def by_student(self, request):
        """Get all payments for a specific student"""
        student_id = request.query_params.get("student_id")

        if not student_id:
            return Response(
                {"error": "student_id parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payments = TuitionPayment.objects.filter(student_id=student_id).order_by(
            "-date"
        )
        serializer = TuitionPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get tuition payment statistics"""
        total_payments = TuitionPayment.objects.count()
        total_collected = (
            TuitionPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        )
        total_outstanding = (
            Student.objects.aggregate(Sum("tuition_balance"))["tuition_balance__sum"]
            or 0
        )

        return Response(
            {
                "total_payments": total_payments,
                "total_collected": float(total_collected),
                "total_outstanding": float(total_outstanding),
            }
        )


# ============== GRADUATION VIEWSETS ==============


class GraduationEventViewSet(viewsets.ModelViewSet):
    """Graduation event management"""

    queryset = GraduationEvent.objects.all().order_by("-event_date")
    serializer_class = GraduationEventSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        """Update event status manually"""
        event = self.get_object()
        new_status = request.data.get("status")

        if not new_status or new_status not in dict(GraduationEvent.STATUS_CHOICES):
            return Response(
                {"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
            )

        event.status = new_status
        event.save()
        return Response({"status": "updated", "new_status": event.status})

    @action(detail=False, methods=["post"])
    def check_statuses(self, request):
        """Update all event statuses based on dates"""
        from django.utils import timezone

        today = timezone.now().date()
        updated_count = 0

        events = GraduationEvent.objects.exclude(status__in=["Completed", "Cancelled"])

        for event in events:
            original_status = event.status
            new_status = original_status

            # Registration -> Closed (deadline passed)
            if event.status == "Registration" and today > event.registration_deadline:
                new_status = "Closed"

            # Any -> Completed (event date passed)
            # Usually event day passing means it's done regardless of registration
            if today > event.event_date and new_status != "Cancelled":
                new_status = "Completed"

            if new_status != original_status:
                event.status = new_status
                event.save()
                updated_count += 1

        return Response(
            {
                "updated_count": updated_count,
                "message": f"Updated status for {updated_count} events",
            }
        )

    def get_queryset(self):
        """Search and filter events"""
        queryset = GraduationEvent.objects.all()
        search = self.request.query_params.get("search", "")
        status = self.request.query_params.get("status", "")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(venue__icontains=search)
            )

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-event_date")

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        """Get event statistics"""
        event = self.get_object()
        return Response(
            {
                "total_participants": event.get_total_participants(),
                "total_paid": float(event.get_total_paid()),
                "total_balance": float(event.get_total_balance()),
                "total_expected_revenue": float(event.get_total_expected_revenue()),
                "is_registration_open": event.is_registration_open(),
            }
        )


class StudentGraduationViewSet(viewsets.ModelViewSet):
    """Student graduation management"""

    queryset = StudentGraduation.objects.all().order_by("-registration_date")
    serializer_class = StudentGraduationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Search and filter student graduations"""
        queryset = StudentGraduation.objects.select_related(
            "student", "graduation_event"
        )

        search = self.request.query_params.get("search", "")
        status = self.request.query_params.get("status", "")
        level = self.request.query_params.get("level", "")
        event_id = self.request.query_params.get("event", "")

        if search:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search)
                | Q(student__last_name__icontains=search)
                | Q(student__lrn__icontains=search)
            )

        if status:
            queryset = queryset.filter(status=status)

        if level:
            queryset = queryset.filter(graduation_level=level)

        if event_id:
            queryset = queryset.filter(graduation_event_id=event_id)

        return queryset.order_by("-registration_date")

    @action(detail=False, methods=["post"])
    def bulk_enroll(self, request):
        """Bulk enroll students from a section"""
        graduation_event_id = request.data.get("graduation_event_id")
        graduation_level = request.data.get("graduation_level")
        section = request.data.get("section")
        student_ids = request.data.get("student_ids", [])

        # Validate required fields
        if not graduation_event_id:
            return Response(
                {"error": "graduation_event_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not graduation_level:
            return Response(
                {"error": "graduation_level is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not section:
            return Response(
                {"error": "section is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not student_ids or len(student_ids) == 0:
            return Response(
                {"error": "student_ids is required (no students found to enroll)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            event = GraduationEvent.objects.get(id=graduation_event_id)
        except GraduationEvent.DoesNotExist:
            return Response(
                {"error": "Graduation event not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check registration status - allow Planning or Registration status
        if event.status not in ["Planning", "Registration"]:
            return Response(
                {
                    "error": f"Registration is closed for this event (status: {event.status})"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if deadline has passed (only if status is Registration)
        if event.status == "Registration" and not event.is_registration_open():
            return Response(
                {"error": "Registration deadline has passed for this event"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check capacity
        if (
            event.max_participants > 0
            and event.get_total_participants() + len(student_ids)
            > event.max_participants
        ):
            return Response(
                {"error": "This would exceed the maximum participants limit"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success_count = 0
        errors = []

        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id)

                # Skip if already enrolled
                if StudentGraduation.objects.filter(
                    graduation_event=event, student=student
                ).exists():
                    errors.append(
                        f"{student.first_name} {student.last_name} is already registered"
                    )
                    continue

                # Create enrollment
                StudentGraduation.objects.create(
                    graduation_event=event,
                    student=student,
                    graduation_level=graduation_level,
                    section=section,
                    total_fee=event.total_fee_per_student,
                )
                success_count += 1

            except Student.DoesNotExist:
                errors.append(f"Student with ID {student_id} not found")

        return Response(
            {
                "success": True,
                "message": f"Successfully enrolled {success_count} students",
                "errors": errors,
            }
        )


class GraduationPaymentViewSet(viewsets.ModelViewSet):
    """Graduation payment management"""

    queryset = GraduationPayment.objects.all().order_by("-payment_date")
    serializer_class = GraduationPaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Create a graduation payment"""
        from django.db import transaction

        student_graduation_id = request.data.get("student_graduation_id")
        amount = request.data.get("amount")
        method = request.data.get("method", "Cash")
        reference_number = request.data.get("reference_number", "")
        gcash_number = request.data.get("gcash_number", "")
        remarks = request.data.get("remarks", "")

        if not student_graduation_id or not amount:
            return Response(
                {"error": "student_graduation_id and amount are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(str(amount))
        except:
            return Response(
                {"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student_graduation = StudentGraduation.objects.get(id=student_graduation_id)
        except StudentGraduation.DoesNotExist:
            return Response(
                {"error": "Student graduation record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than zero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount > student_graduation.balance:
            return Response(
                {
                    "error": f"Amount cannot exceed balance of ₱{student_graduation.balance}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            payment = GraduationPayment.objects.create(
                student_graduation=student_graduation,
                graduation_event=student_graduation.graduation_event,
                student=student_graduation.student,
                amount=amount,
                method=method,
                reference_number=reference_number,
                gcash_number=gcash_number,
                remarks=remarks,
                received_by=request.user.username,
            )

            # Refresh student_graduation to get updated balance and status
            student_graduation.refresh_from_db()

        # Include updated enrollment data in response so frontend can sync status
        payment_serializer = GraduationPaymentSerializer(payment)
        enrollment_serializer = StudentGraduationSerializer(student_graduation)

        return Response(
            {
                "payment": payment_serializer.data,
                "enrollment": enrollment_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def by_student(self, request):
        """Get all payments for a specific student"""
        student_id = request.query_params.get("student_id")

        if not student_id:
            return Response(
                {"error": "student_id parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payments = GraduationPayment.objects.filter(student_id=student_id).order_by(
            "-payment_date"
        )
        serializer = GraduationPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get graduation payment statistics"""
        total_payments = GraduationPayment.objects.count()
        total_collected = (
            GraduationPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        )

        return Response(
            {
                "total_payments": total_payments,
                "total_collected": float(total_collected),
            }
        )


# ============== ASSESSMENT VIEWSETS ==============


class AssessmentTypeViewSet(viewsets.ModelViewSet):
    """Assessment type management"""

    queryset = AssessmentType.objects.all()
    serializer_class = AssessmentTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter to active by default for list, but allow all for detail/update/delete"""
        if self.action == "list":
            return AssessmentType.objects.filter(is_active=True)
        return AssessmentType.objects.all()

    @action(detail=False, methods=["get"])
    def by_level(self, request):
        """Get assessment types by level"""
        level = request.query_params.get("level", "ALL")
        types = AssessmentType.objects.filter(
            Q(applicable_to=level) | Q(applicable_to="ALL"), is_active=True
        )
        serializer = AssessmentTypeSerializer(types, many=True)
        return Response(serializer.data)


class StudentAssessmentViewSet(viewsets.ModelViewSet):
    """Student assessment management"""

    queryset = StudentAssessment.objects.all().order_by("-date_assessed")
    serializer_class = StudentAssessmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Create a student assessment"""
        student_id = request.data.get("student_id")
        assessment_type_id = request.data.get("assessment_type_id")

        if not student_id or not assessment_type_id:
            return Response(
                {"error": "student_id and assessment_type_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            student = Student.objects.get(id=student_id)
            assessment_type = AssessmentType.objects.get(id=assessment_type_id)
        except (Student.DoesNotExist, AssessmentType.DoesNotExist):
            return Response(
                {"error": "Student or Assessment Type not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if already exists
        existing_assessment = StudentAssessment.objects.filter(
            student=student, assessment_type=assessment_type
        ).first()
        if existing_assessment:
            return Response(
                {
                    "error": f"Student {student.first_name} {student.last_name} already has this assessment assigned.",
                    "existing_assessment": {
                        "id": existing_assessment.id,
                        "status": existing_assessment.status,
                        "date_assessed": existing_assessment.date_assessed.isoformat(),
                        "total_fee": float(existing_assessment.total_fee),
                        "amount_paid": float(existing_assessment.amount_paid),
                        "balance": float(existing_assessment.balance),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_fee = request.data.get("total_fee", assessment_type.amount)

        assessment = StudentAssessment.objects.create(
            student=student,
            assessment_type=assessment_type,
            total_fee=total_fee,
            balance=total_fee,
            notes=request.data.get("notes", ""),
            assessed_by=request.data.get("assessed_by", request.user.username),
        )

        serializer = StudentAssessmentSerializer(assessment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def by_student(self, request):
        """Get assessments by student"""
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        assessments = StudentAssessment.objects.filter(student_id=student_id)
        serializer = StudentAssessmentSerializer(assessments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get all pending assessments (with outstanding balance)"""
        assessments = StudentAssessment.objects.filter(
            status__in=["Pending", "Partial"], balance__gt=0
        ).order_by("-date_assessed")
        serializer = StudentAssessmentSerializer(assessments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_enroll(self, request):
        """Bulk assign assessments to students from a section"""
        assessment_type_id = request.data.get("assessment_type_id")
        section = request.data.get("section")
        student_ids = request.data.get("student_ids", [])

        if not all([assessment_type_id, student_ids]):
            return Response(
                {"error": "assessment_type_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assessment_type = AssessmentType.objects.get(id=assessment_type_id)
        except AssessmentType.DoesNotExist:
            return Response(
                {"error": "Assessment type not found"}, status=status.HTTP_404_NOT_FOUND
            )

        success_count = 0
        errors = []

        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id)

                # Skip if already has this assessment
                if StudentAssessment.objects.filter(
                    student=student, assessment_type=assessment_type
                ).exists():
                    errors.append(
                        f"{student.first_name} {student.last_name} already has this assessment"
                    )
                    continue

                # Create assessment
                StudentAssessment.objects.create(
                    student=student,
                    assessment_type=assessment_type,
                    total_fee=assessment_type.amount,
                    balance=assessment_type.amount,
                    notes=f"Bulk assigned from section {section}"
                    if section
                    else "Bulk assigned",
                    assessed_by=request.user.username,
                )
                success_count += 1

            except Student.DoesNotExist:
                errors.append(f"Student with ID {student_id} not found")

        return Response(
            {
                "success": True,
                "message": f"Successfully assigned assessment to {success_count} students",
                "assigned_count": success_count,
                "errors": errors,
            }
        )


class AssessmentPaymentViewSet(viewsets.ModelViewSet):
    """Assessment payment management"""

    queryset = AssessmentPayment.objects.all().order_by("-payment_date")
    serializer_class = AssessmentPaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Create assessment payment"""
        # Accept both 'assessment_id' and 'assessment' from frontend
        assessment_id = request.data.get("assessment_id") or request.data.get(
            "assessment"
        )
        amount = request.data.get("amount")

        if not assessment_id or not amount:
            return Response(
                {"error": "assessment_id (or assessment) and amount are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assessment = StudentAssessment.objects.get(id=assessment_id)
            amount = Decimal(str(amount))

            # Same guards the tour-payments endpoint applies: no zero or
            # negative collections, and never more than the outstanding
            # balance.
            if amount <= 0:
                return Response(
                    {"error": "Payment amount must be greater than 0"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if amount > assessment.balance:
                return Response(
                    {
                        "error": f"Payment amount (₱{amount:.2f}) exceeds remaining balance (₱{assessment.balance:.2f})"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except StudentAssessment.DoesNotExist:
            return Response(
                {"error": "Assessment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Store previous balance before payment
        previous_balance = float(assessment.balance)

        payment = AssessmentPayment.objects.create(
            assessment=assessment,
            student=assessment.student,
            assessment_type=assessment.assessment_type,
            amount=amount,
            payment_method=request.data.get("payment_method", "Cash"),
            reference_number=request.data.get("reference_number", ""),
            gcash_number=request.data.get("gcash_number", ""),
            received_by=request.data.get("received_by", request.user.username),
            remarks=request.data.get("remarks", ""),
        )

        # Refresh assessment from database to get updated balance and amount_paid
        assessment.refresh_from_db()

        serializer = AssessmentPaymentSerializer(payment)
        return Response(
            {
                **serializer.data,
                "previous_balance": previous_balance,
                "remaining_balance": float(assessment.balance),
                "total_paid": float(assessment.amount_paid),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def by_student(self, request):
        """Get payments by student"""
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        payments = AssessmentPayment.objects.filter(student_id=student_id)
        serializer = AssessmentPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get assessment payment statistics"""
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncDate, TruncMonth

        # Date filtering
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        queryset = AssessmentPayment.objects.all()

        if date_from:
            queryset = queryset.filter(payment_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(payment_date__date__lte=date_to)

        # Total statistics
        totals = queryset.aggregate(total_amount=Sum("amount"), total_count=Count("id"))

        # Daily breakdown
        daily = (
            queryset.annotate(date=TruncDate("payment_date"))
            .values("date")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-date")
        )

        # Monthly breakdown
        monthly = (
            queryset.annotate(month=TruncMonth("payment_date"))
            .values("month")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-month")
        )

        # By payment method
        by_method = (
            queryset.values("payment_method")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-amount")
        )

        # By assessment type
        by_type = (
            queryset.values("assessment_type__name")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-amount")
        )

        return Response(
            {
                "totals": {
                    "total_amount": float(totals["total_amount"] or 0),
                    "total_count": totals["total_count"] or 0,
                },
                "daily": [
                    {
                        "date": item["date"].isoformat() if item["date"] else None,
                        "amount": float(item["amount"] or 0),
                        "count": item["count"],
                    }
                    for item in daily
                ],
                "monthly": [
                    {
                        "month": item["month"].strftime("%Y-%m")
                        if item["month"]
                        else None,
                        "amount": float(item["amount"] or 0),
                        "count": item["count"],
                    }
                    for item in monthly
                ],
                "by_method": [
                    {
                        "method": item["payment_method"],
                        "amount": float(item["amount"] or 0),
                        "count": item["count"],
                    }
                    for item in by_method
                ],
                "by_type": [
                    {
                        "type": item["assessment_type__name"],
                        "amount": float(item["amount"] or 0),
                        "count": item["count"],
                    }
                    for item in by_type
                ],
            }
        )


# ============== TOUR VIEWSETS ==============


class EducationalTourViewSet(viewsets.ModelViewSet):
    """Educational tour management"""

    queryset = EducationalTour.objects.all().order_by("-tour_date")
    serializer_class = EducationalTourSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Get upcoming tours"""
        from django.utils import timezone

        tours = EducationalTour.objects.filter(
            tour_date__gte=timezone.now().date(), status__in=["Planned", "Ongoing"]
        )
        serializer = EducationalTourSerializer(tours, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def enrollments(self, request, pk=None):
        """Get enrollments for a tour"""
        tour = self.get_object()
        enrollments = tour.enrollments.all()
        serializer = TourEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get tour statistics"""
        total_tours = EducationalTour.objects.count()
        active_tours = EducationalTour.objects.filter(
            status__in=["Planned", "Ongoing"]
        ).count()
        total_enrollments = TourEnrollment.objects.count()
        total_collected = (
            TourPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        )

        return Response(
            {
                "total_tours": total_tours,
                "active_tours": active_tours,
                "total_enrollments": total_enrollments,
                "total_collected": float(total_collected),
            }
        )


class TourEnrollmentViewSet(viewsets.ModelViewSet):
    """Tour enrollment management"""

    queryset = TourEnrollment.objects.all().order_by("-enrollment_date")
    serializer_class = TourEnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Enroll a student in a tour"""
        tour_id = request.data.get("tour_id") or request.data.get("tour")
        student_id = request.data.get("student_id") or request.data.get("student")

        if not tour_id or not student_id:
            return Response(
                {"error": "tour_id and student_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tour = EducationalTour.objects.get(id=tour_id)
            student = Student.objects.get(id=student_id)
        except (EducationalTour.DoesNotExist, Student.DoesNotExist):
            return Response(
                {"error": "Tour or Student not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if already enrolled
        existing_enrollment = TourEnrollment.objects.filter(
            tour=tour, student=student
        ).first()
        if existing_enrollment:
            return Response(
                {
                    "error": f"Student {student.first_name} {student.last_name} is already enrolled in this tour.",
                    "existing_enrollment": {
                        "id": existing_enrollment.id,
                        "status": existing_enrollment.status,
                        "enrollment_date": existing_enrollment.enrollment_date.isoformat(),
                        "total_fee": float(existing_enrollment.total_fee),
                        "amount_paid": float(existing_enrollment.amount_paid),
                        "balance": float(existing_enrollment.balance),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check slots
        if not tour.has_slots_available():
            return Response(
                {"error": "No slots available for this tour"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_fee = request.data.get("total_fee", tour.total_cost)

        enrollment = TourEnrollment.objects.create(
            tour=tour,
            student=student,
            total_fee=total_fee,
            balance=total_fee,
            parent_consent=request.data.get("parent_consent", False),
            medical_clearance=request.data.get("medical_clearance", False),
            notes=request.data.get("notes", ""),
        )

        serializer = TourEnrollmentSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def by_student(self, request):
        """Get enrollments by student"""
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        enrollments = TourEnrollment.objects.filter(student_id=student_id)
        serializer = TourEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_tour(self, request):
        """Get enrollments by tour"""
        tour_id = request.query_params.get("tour_id")
        if not tour_id:
            return Response(
                {"error": "tour_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        enrollments = TourEnrollment.objects.filter(tour_id=tour_id)
        serializer = TourEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get all pending tour enrollments (with outstanding balance)"""
        enrollments = TourEnrollment.objects.filter(
            status__in=["Enrolled", "Partial"], balance__gt=0
        ).order_by("-enrollment_date")
        serializer = TourEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_enroll(self, request):
        """Bulk enroll students in a tour from a section"""
        tour_id = request.data.get("tour_id")
        section = request.data.get("section")
        student_ids = request.data.get("student_ids", [])

        if not all([tour_id, student_ids]):
            return Response(
                {"error": "tour_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tour = EducationalTour.objects.get(id=tour_id)
        except EducationalTour.DoesNotExist:
            return Response(
                {"error": "Tour not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check slots availability
        available_slots = (
            tour.max_participants - tour.get_total_participants()
            if tour.max_participants > 0
            else len(student_ids)
        )
        if len(student_ids) > available_slots:
            return Response(
                {
                    "error": f"Not enough slots available. Only {available_slots} slots remaining."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        success_count = 0
        errors = []

        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id)

                # Skip if already enrolled
                if TourEnrollment.objects.filter(tour=tour, student=student).exists():
                    errors.append(
                        f"{student.first_name} {student.last_name} is already enrolled"
                    )
                    continue

                # Create enrollment
                TourEnrollment.objects.create(
                    tour=tour,
                    student=student,
                    total_fee=tour.total_cost,
                    balance=tour.total_cost,
                    parent_consent=False,
                    medical_clearance=False,
                    notes=f"Bulk enrolled from section {section}"
                    if section
                    else "Bulk enrolled",
                )
                success_count += 1

            except Student.DoesNotExist:
                errors.append(f"Student with ID {student_id} not found")

        return Response(
            {
                "success": True,
                "message": f"Successfully enrolled {success_count} students",
                "enrolled_count": success_count,
                "errors": errors,
            }
        )


class TourPaymentViewSet(viewsets.ModelViewSet):
    """Tour payment management"""

    queryset = TourPayment.objects.all().order_by("-payment_date")
    serializer_class = TourPaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Create tour payment"""
        # Accept both spellings callers have used; ToursPage sends
        # tour_enrollment, older payloads enrollment_id.
        enrollment_id = request.data.get("enrollment_id") or request.data.get(
            "tour_enrollment"
        )
        amount = request.data.get("amount")

        if not enrollment_id or not amount:
            return Response(
                {"error": "enrollment_id and amount are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            enrollment = TourEnrollment.objects.get(id=enrollment_id)
            amount = Decimal(str(amount))

            # Prevent payments that exceed the remaining balance
            if amount > enrollment.balance:
                return Response(
                    {
                        "error": f"Payment amount (₱{amount:.2f}) exceeds remaining balance (₱{enrollment.balance:.2f})"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Prevent negative or zero payments
            if amount <= 0:
                return Response(
                    {"error": "Payment amount must be greater than 0"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except TourEnrollment.DoesNotExist:
            return Response(
                {"error": "Enrollment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST
            )

        payment = TourPayment.objects.create(
            enrollment=enrollment,
            tour=enrollment.tour,
            student=enrollment.student,
            amount=amount,
            # Callers send payment_method (the shared payment modal); the
            # legacy field name here is method.
            method=request.data.get("method") or request.data.get("payment_method", "Cash"),
            reference_number=request.data.get("reference_number", ""),
            received_by=request.data.get("received_by", request.user.username),
            remarks=request.data.get("remarks", ""),
        )

        serializer = TourPaymentSerializer(payment)
        return Response(
            {
                **serializer.data,
                "previous_balance": float(enrollment.balance + amount),
                "remaining_balance": float(enrollment.balance),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def by_student(self, request):
        """Get payments by student"""
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        payments = TourPayment.objects.filter(student_id=student_id)
        serializer = TourPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_tour(self, request):
        """Get payments by tour"""
        tour_id = request.query_params.get("tour_id")
        if not tour_id:
            return Response(
                {"error": "tour_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        payments = TourPayment.objects.filter(tour_id=tour_id)
        serializer = TourPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get tour payment statistics"""
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncDate, TruncMonth

        # Date filtering
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        queryset = TourPayment.objects.all()

        if date_from:
            queryset = queryset.filter(payment_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(payment_date__date__lte=date_to)

        # Total statistics
        totals = queryset.aggregate(total_amount=Sum("amount"), total_count=Count("id"))

        # Daily breakdown
        daily = (
            queryset.annotate(date=TruncDate("payment_date"))
            .values("date")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-date")
        )

        # Monthly breakdown
        monthly = (
            queryset.annotate(month=TruncMonth("payment_date"))
            .values("month")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-month")
        )

        # By payment method
        by_method = (
            queryset.values("method")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-amount")
        )

        # By tour
        by_tour = (
            queryset.values("tour__name")
            .annotate(amount=Sum("amount"), count=Count("id"))
            .order_by("-amount")
        )

        return Response(
            {
                "totals": {
                    "total_amount": float(totals["total_amount"] or 0),
                    "total_count": totals["total_count"] or 0,
                },
                "daily": [
                    {
                        "date": item["date"].isoformat() if item["date"] else None,
                        "amount": float(item["amount"] or 0),
                        "count": item["count"],
                    }
                    for item in daily
                ],
                "monthly": [
                    {
                        "month": item["month"].strftime("%Y-%m")
                        if item["month"]
                        else None,
                        "amount": float(item["amount"] or 0),
                        "count": item["count"],
                    }
                    for item in monthly
                ],
                "by_method": [
                    {
                        "method": item["method"],
                        "amount": float(item["amount"] or 0),
                        "count": item["count"],
                    }
                    for item in by_method
                ],
                "by_tour": [
                    {
                        "tour": item["tour__name"],
                        "amount": float(item["amount"] or 0),
                        "count": item["count"],
                    }
                    for item in by_tour
                ],
            }
        )


# ============== REVENUE VIEWSET ==============


class RevenueViewSet(viewsets.ViewSet):
    """Revenue dashboard and reporting"""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get revenue dashboard data"""
        search_query = request.query_params.get("search", "")
        revenue_type = request.query_params.get("type", "")
        payment_method = request.query_params.get("method", "")
        date_from = request.query_params.get("date_from", "")
        date_to = request.query_params.get("date_to", "")

        revenue_list = []

        # POS transactions come from the Sale itself, not from Payment rows
        # that happen to point at one. The Cashier records a product sale
        # directly, so keying off a linked Payment meant every uniform and
        # supplies sale was absent from this dashboard entirely even though
        # the money was taken. Only sales that actually collected money count.
        pos_sales = (
            Sale.objects.filter(amount_paid__gt=0)
            .select_related("student")
            .prefetch_related("items__product")
        )

        # Get tuition payments
        tuition_payments = TuitionPayment.objects.all().select_related("student")

        # Get assessment payments
        assessment_payments = AssessmentPayment.objects.all().select_related("student", "assessment_type")

        # Get dorm payments
        dorm_payments = DormPayment.objects.all().select_related(
            "assignment", "assignment__student", "assignment__room"
        )

        # Get tour payments
        tour_payments = TourPayment.objects.all().select_related(
            "student", "tour"
        )

        # Get graduation payments
        graduation_payments = GraduationPayment.objects.all().select_related("student", "graduation_event")

        # Get general payments (Miscellaneous, Laboratory, Assessment, Other OR walk-in payments without a sale)
        # The final clause is a backstop: rows written by older builds of the
        # Cashier page never sent payment_type and are not walk-in, so they
        # matched neither branch and vanished from Revenue entirely even though
        # the money was collected. They are recovered here, with the type parsed
        # back out of the free-text remarks ("Miscellaneous - Type - B Uniform").
        general_payments = Payment.objects.filter(
            Q(payment_type__in=['Miscellaneous', 'Laboratory', 'Assessment', 'Other', 'Graduation'])
            | Q(is_walk_in=True, sale__isnull=True)
            | Q(payment_type__isnull=True, sale__isnull=True, is_walk_in=False)
        ).select_related("student")

        # Filter POS sales
        if revenue_type == "" or revenue_type == "pos":
            if search_query:
                pos_sales = pos_sales.filter(
                    Q(customer_name__icontains=search_query)
                    | Q(student__first_name__icontains=search_query)
                    | Q(student__last_name__icontains=search_query)
                    | Q(student__lrn__icontains=search_query)
                    | Q(items__product__name__icontains=search_query)
                ).distinct()
            if payment_method:
                pos_sales = pos_sales.filter(payment_method__iexact=payment_method)
            if date_from:
                pos_sales = pos_sales.filter(created_at__date__gte=date_from)
            if date_to:
                pos_sales = pos_sales.filter(created_at__date__lte=date_to)

            for sale in pos_sales:
                if sale.student:
                    customer = f"{sale.student.first_name} {sale.student.last_name}"
                elif sale.customer_name:
                    customer = sale.customer_name
                else:
                    customer = "Walk-in Customer"

                # Get product details
                products_list = []
                for item in sale.items.all():
                    if item.product:
                        product_name = item.product.name
                    else:
                        product_name = (
                            item.custom_item_name or ""
                        ).strip() or "Custom Item"

                    products_list.append(
                        {
                            "name": product_name,
                            "quantity": item.quantity,
                            "price": float(item.price),
                            "size": item.size,
                        }
                    )

                revenue_list.append(
                    {
                        "id": sale.id,
                        "kind": "sale",
                        "entry_id": f"sale-{sale.id}",
                        "type": "POS",
                        "date": sale.created_at.isoformat(),
                        "customer": customer,
                        "amount": float(sale.amount_paid),
                        "method": sale.payment_method,
                        # The cashier's OR number; null only for sales
                        # recorded before it was stored.
                        "reference": sale.receipt_number or "-",
                        "products": products_list,
                    }
                )

        # Filter tuition payments
        if revenue_type == "" or revenue_type == "tuition":
            if search_query:
                tuition_payments = tuition_payments.filter(
                    Q(student__first_name__icontains=search_query)
                    | Q(student__last_name__icontains=search_query)
                    | Q(student__lrn__icontains=search_query)
                )
            if payment_method:
                tuition_payments = tuition_payments.filter(method=payment_method)
            if date_from:
                tuition_payments = tuition_payments.filter(date__gte=date_from)
            if date_to:
                tuition_payments = tuition_payments.filter(date__lte=date_to)

            for payment in tuition_payments:
                customer = f"{payment.student.first_name} {payment.student.last_name}"

                revenue_list.append(
                    {
                        "id": payment.id,
                        "kind": "tuition",
                        "entry_id": f"tuition-{payment.id}",
                        "type": "Tuition",
                        "date": payment.date.isoformat(),
                        "customer": customer,
                        "amount": float(payment.amount),
                        "method": payment.method,
                        "reference": _or_no(payment.reference_no, payment.date, payment.id),
                        "products": [
                            {
                                "name": payment.remarks.strip() if payment.remarks else "Tuition Fee",
                                "quantity": 1,
                                "price": float(payment.amount),
                            }
                        ],
                    }
                )

        # Filter assessment payments
        if revenue_type == "" or revenue_type == "assessment":
            if search_query:
                assessment_payments = assessment_payments.filter(
                    Q(student__first_name__icontains=search_query)
                    | Q(student__last_name__icontains=search_query)
                    | Q(student__lrn__icontains=search_query)
                )
            if payment_method:
                assessment_payments = assessment_payments.filter(
                    payment_method=payment_method
                )
            if date_from:
                assessment_payments = assessment_payments.filter(
                    payment_date__gte=date_from
                )
            if date_to:
                assessment_payments = assessment_payments.filter(
                    payment_date__lte=date_to
                )

            for payment in assessment_payments:
                customer = f"{payment.student.first_name} {payment.student.last_name}"
                assessment_name = (
                    payment.assessment_type.name
                    if payment.assessment_type
                    else "Assessment"
                )

                revenue_list.append(
                    {
                        "id": payment.id,
                        "kind": "assessment",
                        "entry_id": f"assessment-{payment.id}",
                        "type": "Assessment",
                        "date": payment.payment_date.isoformat(),
                        "customer": customer,
                        "amount": float(payment.amount),
                        "method": payment.payment_method,
                        "reference": _or_no(payment.reference_number, payment.payment_date, payment.id),
                        "products": [
                            {
                                "name": assessment_name,
                                "quantity": 1,
                                "price": float(payment.amount),
                            }
                        ],
                    }
                )

        # Filter dorm payments
        if revenue_type == "" or revenue_type == "dorm":
            if search_query:
                dorm_payments = dorm_payments.filter(
                    Q(assignment__student__first_name__icontains=search_query)
                    | Q(assignment__student__last_name__icontains=search_query)
                    | Q(assignment__student__lrn__icontains=search_query)
                )
            if payment_method:
                dorm_payments = dorm_payments.filter(payment_method=payment_method)
            if date_from:
                dorm_payments = dorm_payments.filter(payment_date__gte=date_from)
            if date_to:
                dorm_payments = dorm_payments.filter(payment_date__lte=date_to)

            for payment in dorm_payments:
                customer = f"{payment.assignment.student.first_name} {payment.assignment.student.last_name}"
                dorm_info = (
                    payment.assignment.room.room_number
                    if payment.assignment.room
                    else "Dorm"
                )

                revenue_list.append(
                    {
                        "id": payment.id,
                        "kind": "dorm",
                        "entry_id": f"dorm-{payment.id}",
                        "type": "Dorm",
                        "date": payment.payment_date.isoformat(),
                        "customer": customer,
                        "amount": float(payment.amount),
                        "method": payment.payment_method,
                        "reference": payment.receipt_number or "-",
                        "products": [
                            {
                                "name": f"Dorm - {dorm_info} ({payment.month_covered} {payment.year_covered})",
                                "quantity": 1,
                                "price": float(payment.amount),
                            }
                        ],
                    }
                )

        # Filter tour payments
        if revenue_type == "" or revenue_type == "tour":
            if search_query:
                tour_payments = tour_payments.filter(
                    Q(student__first_name__icontains=search_query)
                    | Q(student__last_name__icontains=search_query)
                    | Q(student__lrn__icontains=search_query)
                )
            if payment_method:
                tour_payments = tour_payments.filter(method=payment_method)
            if date_from:
                tour_payments = tour_payments.filter(payment_date__gte=date_from)
            if date_to:
                tour_payments = tour_payments.filter(payment_date__lte=date_to)

            for payment in tour_payments:
                customer = f"{payment.student.first_name} {payment.student.last_name}"
                tour_name = payment.tour.name if payment.tour else "Educational Tour"

                revenue_list.append(
                    {
                        "id": payment.id,
                        "kind": "tour",
                        "entry_id": f"tour-{payment.id}",
                        "type": "Tour",
                        "date": payment.payment_date.isoformat(),
                        "customer": customer,
                        "amount": float(payment.amount),
                        "method": payment.method,
                        "reference": _or_no(payment.reference_number, payment.payment_date, payment.id),
                        "products": [
                            {
                                "name": tour_name,
                                "quantity": 1,
                                "price": float(payment.amount),
                            }
                        ],
                    }
                )

        # Filter graduation payments
        if revenue_type == "" or revenue_type == "graduation":
            if search_query:
                graduation_payments = graduation_payments.filter(
                    Q(student__first_name__icontains=search_query)
                    | Q(student__last_name__icontains=search_query)
                    | Q(student__lrn__icontains=search_query)
                )
            if payment_method:
                graduation_payments = graduation_payments.filter(method=payment_method)
            if date_from:
                graduation_payments = graduation_payments.filter(
                    payment_date__gte=date_from
                )
            if date_to:
                graduation_payments = graduation_payments.filter(
                    payment_date__lte=date_to
                )

            for payment in graduation_payments:
                customer = f"{payment.student.first_name} {payment.student.last_name}"
                event_name = (
                    payment.graduation_event.name
                    if payment.graduation_event
                    else "Graduation"
                )

                revenue_list.append(
                    {
                        "id": payment.id,
                        "kind": "graduation",
                        "entry_id": f"graduation-{payment.id}",
                        "type": "Graduation",
                        "date": payment.payment_date.isoformat(),
                        "customer": customer,
                        "amount": float(payment.amount),
                        "method": payment.method,
                        "reference": _or_no(payment.reference_number, payment.payment_date, payment.id),
                        "products": [
                            {
                                "name": event_name,
                                "quantity": 1,
                                "price": float(payment.amount),
                            }
                        ],
                    }
                )

        # Filter general payments (Miscellaneous, Laboratory, Assessment, Other)
        if revenue_type == "" or revenue_type == "general":
            if search_query:
                general_payments = general_payments.filter(
                    Q(payer_name__icontains=search_query)
                    | Q(student__first_name__icontains=search_query)
                    | Q(student__last_name__icontains=search_query)
                    | Q(student__lrn__icontains=search_query)
                )
            if payment_method:
                general_payments = general_payments.filter(payment_method=payment_method)
            if date_from:
                general_payments = general_payments.filter(created_at__date__gte=date_from)
            if date_to:
                general_payments = general_payments.filter(created_at__date__lte=date_to)

            for payment in general_payments:
                if payment.student:
                    customer = f"{payment.student.first_name} {payment.student.last_name}"
                else:
                    customer = payment.payer_name or "Walk-in"

                revenue_list.append(
                    {
                        "id": payment.id,
                        "kind": "payment",
                        "entry_id": f"payment-{payment.id}",
                        "type": payment.payment_type or "General",
                        "date": payment.created_at.isoformat(),
                        "customer": customer,
                        "amount": float(payment.amount),
                        "method": payment.payment_method,
                        "reference": _or_no(payment.reference_number, payment.created_at, payment.id),
                        "products": [
                            {
                                "name": payment.remarks.strip() if payment.remarks else payment.payment_type or "General Payment",
                                "quantity": 1,
                                "price": float(payment.amount),
                            }
                        ],
                    }
                )

        # Sort by date (newest first)
        revenue_list = sorted(revenue_list, key=lambda x: x["date"], reverse=True)

        # Calculate totals.
        # POS totals come from Sale.amount_paid so they match the transaction
        # list above; a linked-Payment basis excluded every cashier sale.
        # Uses the same filtered querysets as the list so the date range,
        # search and type filters apply to the figures, not just the rows.
        total_pos = pos_sales.aggregate(t=Sum("amount_paid"))["t"] or 0
        total_tuition = (
            TuitionPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        )
        total_assessment = (
            AssessmentPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        )
        total_dorm = DormPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        total_tour = TourPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        total_graduation = (
            GraduationPayment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        )
        total_general = (
            Payment.objects.filter(
                Q(payment_type__in=['Miscellaneous', 'Laboratory', 'Assessment', 'Other', 'Graduation'])
                | Q(is_walk_in=True, sale__isnull=True)
                | Q(payment_type__isnull=True, sale__isnull=True, is_walk_in=False)
            ).aggregate(Sum("amount"))["amount__sum"] or 0
        )
        total_revenue = (
            total_pos
            + total_tuition
            + total_assessment
            + total_dorm
            + total_tour
            + total_graduation
            + total_general
        )

        # Count transactions
        pos_count = pos_sales.count()
        tuition_count = TuitionPayment.objects.count()
        assessment_count = AssessmentPayment.objects.count()
        dorm_count = DormPayment.objects.count()
        tour_count = TourPayment.objects.count()
        graduation_count = GraduationPayment.objects.count()
        general_count = Payment.objects.filter(
            Q(payment_type__in=['Miscellaneous', 'Laboratory', 'Assessment', 'Other', 'Graduation'])
            | Q(is_walk_in=True, sale__isnull=True)
            | Q(payment_type__isnull=True, sale__isnull=True, is_walk_in=False)
        ).count()
        total_transactions = (
            pos_count
            + tuition_count
            + assessment_count
            + dorm_count
            + tour_count
            + graduation_count
            + general_count
        )

        return Response(
            {
                "revenue": revenue_list,
                "totals": {
                    "total_revenue": float(total_revenue),
                    "total_pos": float(total_pos),
                    "total_tuition": float(total_tuition),
                    "total_assessment": float(total_assessment),
                    "total_dorm": float(total_dorm),
                    "total_tour": float(total_tour),
                    "total_graduation": float(total_graduation),
                    "total_general": float(total_general),
                    "total_transactions": total_transactions,
                    "pos_count": pos_count,
                    "tuition_count": tuition_count,
                    "assessment_count": assessment_count,
                    "dorm_count": dorm_count,
                    "tour_count": tour_count,
                    "graduation_count": graduation_count,
                    "general_count": general_count,
                },
            }
        )

    # Map a revenue row's `kind` to the model that actually stores it. Revenue
    # aggregates seven different tables and every one of them numbers its rows
    # from 1, so a bare id is ambiguous - id 5 could be a payment or a sale.
    REVENUE_ENTRY_MODELS = {
        "sale": ("sales.models", "Sale"),
        "payment": ("payments.models", "Payment"),
        "tuition": ("tuition.models", "TuitionPayment"),
        "assessment": ("assessment.models", "AssessmentPayment"),
        "dorm": ("dorm.models", "DormPayment"),
        "tour": ("tours.models", "TourPayment"),
        "graduation": ("graduation.models", "GraduationPayment"),
    }

    def _resolve_entry(self, request):
        """Resolve ?kind=&id= to a model instance, or return an error Response."""
        kind = request.query_params.get("kind") or request.data.get("kind")
        raw_id = request.query_params.get("id") or request.data.get("id")
        target = self.REVENUE_ENTRY_MODELS.get(kind)
        if target is None:
            return None, Response(
                {"error": f"Unknown revenue entry kind '{kind}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pk = int(raw_id)
        except (TypeError, ValueError):
            return None, Response(
                {"error": "A numeric id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        module_path, model_name = target
        model = getattr(import_module(module_path), model_name)
        obj = model.objects.filter(pk=pk).first()
        if obj is None:
            return None, Response(
                {"error": f"No {kind} entry with id {pk}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return obj, None

    @action(detail=False, methods=["patch", "delete"], url_path="entry")
    def entry(self, request):
        """Edit or remove a single revenue entry, addressed by ?kind=&id=.

        One action rather than two: separate @action methods sharing a
        url_path collide on the same route and DRF silently keeps only one, so
        PATCH came back 405 Method Not Allowed.

        PATCH corrects descriptive fields. The amount is deliberately not
        editable - changing it would rewrite financial history with no
        matching payment row, so a wrong amount should be deleted and
        re-entered instead.
        DELETE removes a mistyped entry; it disappears from Revenue, the
        cashier ledger and the SOA payment history together.
        """
        obj, error = self._resolve_entry(request)
        if error:
            return error

        kind = request.query_params.get("kind") or request.data.get("kind")

        if request.method == "DELETE":
            label = getattr(obj, "item_name", None) or str(obj)
            obj.delete()
            # Through the logger, not print(): the Windows console codepage
            # cannot encode the peso sign in a label, which raised
            # UnicodeEncodeError AFTER the delete had committed - so the
            # caller saw a 500 for a deletion that had actually happened.
            logger.info("[revenue] %s deleted %s entry %r", request.user, kind, label)
            return Response({"success": True, "kind": kind, "deleted": True})

        changed = {}
        for field in ("payment_method", "method", "notes", "remarks",
                      "reference_number", "payment_type", "status"):
            if field in request.data and hasattr(obj, field):
                value = request.data[field]
                setattr(obj, field, value)
                changed[field] = value
        if not changed:
            return Response(
                {"error": "No editable fields supplied."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.save()
        return Response({
            "success": True,
            "kind": kind,
            "id": obj.pk,
            "changed": changed,
        })

    @action(detail=False, methods=["get"])
    def report(self, request):
        """Generate revenue report"""
        from django.utils import timezone
        from datetime import timedelta

        date_from = request.query_params.get("date_from", "")
        date_to = request.query_params.get("date_to", "")
        report_type = request.query_params.get("type", "all")

        # Parse dates and set defaults.
        # These boundaries must be LOCAL dates. USE_TZ=True means a
        # `created_at__date` lookup buckets rows by TIME_ZONE (Asia/Manila),
        # while timezone.now() is UTC - so computing "today" from UTC made
        # every sale after 16:00 Manila land on tomorrow's bucket and fall
        # outside the window. Local dates keep the two in step.
        local_today = timezone.localtime().date()

        if date_from:
            start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        else:
            start_date = local_today.replace(day=1)
            date_from = start_date.strftime("%Y-%m-%d")

        if date_to:
            end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            end_date = end_date + timedelta(days=1)
        else:
            end_date = local_today + timedelta(days=1)
            date_to = (end_date - timedelta(days=1)).strftime("%Y-%m-%d")

        # Initialize data
        pos_sales_list = []
        tuition_payments_list = []
        assessment_payments_list = []
        dorm_payments_list = []
        tour_payments_list = []
        graduation_payments_list = []
        general_payments_list = []

        # Get POS Sales
        if report_type in ["all", "pos"]:
            pos_sales_query = (
                Sale.objects.filter(
                    amount_paid__gt=0,
                    created_at__date__gte=start_date,
                    created_at__date__lt=end_date,
                )
                .select_related("student")
                .prefetch_related("payments", "items__product")
                .order_by("-created_at")
            )

            for sale in pos_sales_query:
                if sale.student:
                    customer = f"{sale.student.first_name} {sale.student.last_name}"
                elif sale.customer_name:
                    customer = sale.customer_name
                else:
                    customer = "Walk-in Customer"

                payment_method = "N/A"
                if sale.payments.exists():
                    payment_method = sale.payments.first().payment_method

                # Get product details
                products_list = []
                for item in sale.items.all():
                    if item.product:
                        product_name = item.product.name
                    elif item.custom_item_name:
                        product_name = item.custom_item_name
                    else:
                        product_name = "Custom Item"

                    products_list.append(
                        {
                            "name": product_name,
                            "quantity": item.quantity,
                            "price": float(item.price),
                        }
                    )

                pos_sales_list.append(
                    {
                        "id": sale.id,
                        "date": sale.created_at.isoformat(),
                        "customer": customer,
                        # amount_paid, not total: these must agree with
                        # /api/revenue/, which reports cash actually taken.
                        "amount": float(sale.amount_paid),
                        "method": payment_method,
                        "reference": sale.receipt_number or "-",
                        "products": products_list,
                    }
                )

            pos_sales_total = (
                pos_sales_query.aggregate(total=Sum("amount_paid"))["total"] or 0
            )
        else:
            pos_sales_total = 0

        # Get Tuition Payments
        if report_type in ["all", "tuition"]:
            tuition_payments_query = (
                TuitionPayment.objects.filter(date__gte=start_date, date__lt=end_date)
                .select_related("student")
                .order_by("-date")
            )

            for payment in tuition_payments_query:
                tuition_payments_list.append(
                    {
                        "id": payment.id,
                        "date": payment.date.isoformat(),
                        "customer": f"{payment.student.first_name} {payment.student.last_name}",
                        "amount": float(payment.amount),
                        "method": payment.method,
                        "reference": _or_no(payment.reference_no, payment.date, payment.id),
                    }
                )

            tuition_payments_total = (
                tuition_payments_query.aggregate(total=Sum("amount"))["total"] or 0
            )
        else:
            tuition_payments_total = 0

        # Get Assessment Payments
        if report_type in ["all", "assessment"]:
            assessment_payments_query = (
                AssessmentPayment.objects.filter(
                    payment_date__gte=start_date, payment_date__lt=end_date
                )
                .select_related("student", "assessment_type")
                .order_by("-payment_date")
            )

            for payment in assessment_payments_query:
                assessment_payments_list.append(
                    {
                        "id": payment.id,
                        "date": payment.payment_date.isoformat(),
                        "customer": f"{payment.student.first_name} {payment.student.last_name}",
                        "amount": float(payment.amount),
                        "method": payment.payment_method,
                        "reference": _or_no(payment.reference_number, payment.payment_date, payment.id),
                        "assessment_type": payment.assessment_type.name,
                    }
                )

            assessment_payments_total = (
                assessment_payments_query.aggregate(total=Sum("amount"))["total"] or 0
            )
        else:
            assessment_payments_total = 0

        # Get Dorm Payments
        if report_type in ["all", "dorm"]:
            dorm_payments_query = (
                DormPayment.objects.filter(
                    payment_date__gte=start_date, payment_date__lt=end_date
                )
                .select_related("assignment", "assignment__student", "assignment__room")
                .order_by("-payment_date")
            )

            for payment in dorm_payments_query:
                dorm_info = (
                    payment.assignment.room.room_number
                    if payment.assignment.room
                    else "Dorm"
                )
                dorm_payments_list.append(
                    {
                        "id": payment.id,
                        "date": payment.payment_date.isoformat(),
                        "customer": f"{payment.assignment.student.first_name} {payment.assignment.student.last_name}",
                        "amount": float(payment.amount),
                        "method": payment.payment_method,
                        "reference": payment.receipt_number or "-",
                        "dorm_info": f"{dorm_info} ({payment.month_covered} {payment.year_covered})",
                    }
                )

            dorm_payments_total = (
                dorm_payments_query.aggregate(total=Sum("amount"))["total"] or 0
            )
        else:
            dorm_payments_total = 0

        # Get Tour Payments
        if report_type in ["all", "tour"]:
            tour_payments_query = (
                TourPayment.objects.filter(
                    payment_date__gte=start_date, payment_date__lt=end_date
                )
                .select_related("student", "tour")
                .order_by("-payment_date")
            )

            for payment in tour_payments_query:
                tour_name = payment.tour.name if payment.tour else "Educational Tour"
                tour_payments_list.append(
                    {
                        "id": payment.id,
                        "date": payment.payment_date.isoformat(),
                        "customer": f"{payment.student.first_name} {payment.student.last_name}",
                        "amount": float(payment.amount),
                        "method": payment.method,
                        "reference": _or_no(payment.reference_number, payment.payment_date, payment.id),
                        "tour_name": tour_name,
                    }
                )

            tour_payments_total = (
                tour_payments_query.aggregate(total=Sum("amount"))["total"] or 0
            )
        else:
            tour_payments_total = 0

        # Get Graduation Payments
        if report_type in ["all", "graduation"]:
            graduation_payments_query = (
                GraduationPayment.objects.filter(
                    payment_date__gte=start_date, payment_date__lt=end_date
                )
                .select_related("student", "graduation_event")
                .order_by("-payment_date")
            )

            for payment in graduation_payments_query:
                event_name = (
                    payment.graduation_event.name
                    if payment.graduation_event
                    else "Graduation"
                )
                graduation_payments_list.append(
                    {
                        "id": payment.id,
                        "date": payment.payment_date.isoformat(),
                        "customer": f"{payment.student.first_name} {payment.student.last_name}",
                        "amount": float(payment.amount),
                        "method": payment.method,
                        "reference": _or_no(payment.reference_number, payment.payment_date, payment.id),
                        "event_name": event_name,
                    }
                )

            graduation_payments_total = (
                graduation_payments_query.aggregate(total=Sum("amount"))["total"] or 0
            )
        else:
            graduation_payments_total = 0

        # Get General Payments (Miscellaneous, Laboratory, Assessment, Other)
        if report_type in ["all", "general"]:
            general_payments_query = (
                Payment.objects.filter(
                    created_at__gte=start_date,
                    created_at__lt=end_date,
                ).filter(
                    Q(payment_type__in=['Miscellaneous', 'Laboratory', 'Assessment', 'Other', 'Graduation'])
                    | Q(is_walk_in=True, sale__isnull=True)
                )
                .select_related("student")
                .order_by("-created_at")
            )

            for payment in general_payments_query:
                if payment.student:
                    customer = f"{payment.student.first_name} {payment.student.last_name}"
                else:
                    customer = payment.payer_name or "Walk-in"

                general_payments_list.append(
                    {
                        "id": payment.id,
                        "date": payment.created_at.isoformat(),
                        "customer": customer,
                        "amount": float(payment.amount),
                        "method": payment.payment_method,
                        "reference": _or_no(payment.reference_number, payment.created_at, payment.id),
                        "payment_type": payment.payment_type or "General",
                        "is_walk_in": payment.is_walk_in,
                        "remarks": payment.remarks,
                    }
                )

            general_payments_total = (
                general_payments_query.aggregate(total=Sum("amount"))["total"] or 0
            )
        else:
            general_payments_total = 0

        # Calculate grand total
        grand_total = (
            pos_sales_total
            + tuition_payments_total
            + assessment_payments_total
            + dorm_payments_total
            + tour_payments_total
            + graduation_payments_total
            + general_payments_total
        )

        # Count transactions
        pos_count = len(pos_sales_list)
        tuition_count = len(tuition_payments_list)
        assessment_count = len(assessment_payments_list)
        dorm_count = len(dorm_payments_list)
        tour_count = len(tour_payments_list)
        graduation_count = len(graduation_payments_list)
        general_count = len(general_payments_list)
        total_transactions = (
            pos_count
            + tuition_count
            + assessment_count
            + dorm_count
            + tour_count
            + graduation_count
            + general_count
        )

        return Response(
            {
                "pos_sales": pos_sales_list,
                "tuition_payments": tuition_payments_list,
                "assessment_payments": assessment_payments_list,
                "dorm_payments": dorm_payments_list,
                "tour_payments": tour_payments_list,
                "graduation_payments": graduation_payments_list,
                "general_payments": general_payments_list,
                "totals": {
                    "pos_sales_total": float(pos_sales_total),
                    "tuition_payments_total": float(tuition_payments_total),
                    "assessment_payments_total": float(assessment_payments_total),
                    "dorm_payments_total": float(dorm_payments_total),
                    "tour_payments_total": float(tour_payments_total),
                    "graduation_payments_total": float(graduation_payments_total),
                    "general_payments_total": float(general_payments_total),
                    "grand_total": float(grand_total),
                    "pos_count": pos_count,
                    "tuition_count": tuition_count,
                    "assessment_count": assessment_count,
                    "dorm_count": dorm_count,
                    "tour_count": tour_count,
                    "graduation_count": graduation_count,
                    "general_count": general_count,
                    "total_transactions": total_transactions,
                },
                "date_from": date_from,
                "date_to": date_to,
                "report_type": report_type,
                "generated_date": timezone.now().isoformat(),
            }
        )


class PaymentViewSet(viewsets.ModelViewSet):
    """Payment CRUD for Miscellaneous/Laboratory/Assessment/Other (non-tuition) payments"""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Payment.objects.all().select_related("student").order_by("-created_at")
        status_filter = self.request.query_params.get("status")
        search = self.request.query_params.get("search", "")
        payment_type = self.request.query_params.get("payment_type")
        student_id = self.request.query_params.get("student_id")

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)

        # Exact match on the account, so a ledger can be scoped to one student
        # without name searches catching a different student with a similar name.
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        if search:
            queryset = queryset.filter(
                Q(payer_name__icontains=search)
                | Q(reference_number__icontains=search)
                | Q(student__first_name__icontains=search)
                | Q(student__last_name__icontains=search)
                | Q(student__lrn__icontains=search)
            )

        return queryset

    @action(detail=False, methods=["get"])
    def ledger(self, request):
        """Everything one student has paid, in one list.

        A student's money is recorded in three places - Payment rows for
        miscellaneous items and charge settlements, Sale rows for products
        bought over the counter, and TuitionPayment rows for tuition. Reading
        only Payment (as the cashier history tab used to) hid the uniforms and
        tuition a student had actually paid for, which made their ledger look
        empty next to a balance they genuinely owed.
        """
        from tuition.models import TuitionPayment as Tuition

        raw_id = request.query_params.get("student_id", "")
        try:
            student_id = int(raw_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "student_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student = get_object_or_404(Student, id=student_id)

        rows = []

        for p in Payment.objects.filter(student_id=student_id).select_related("student"):
            rows.append({
                "kind": "payment",
                "id": f"payment-{p.id}",
                "date": p.created_at,
                "reference": p.reference_number or f"PAY-{p.id}",
                "type": p.payment_type or "Miscellaneous",
                # Payment carries remarks, not notes.
                "description": (p.remarks or "").strip() or None,
                "method": p.payment_method,
                "amount": float(p.amount or 0),
                "status": p.status or "completed",
            })

        for s in Sale.objects.filter(student_id=student_id).prefetch_related("items__variant"):
            lines = [
                f"{it.product.name if it.product else (it.custom_item_name or 'Custom Item')}"
                + (f" ({it.size})" if it.size else "")
                for it in s.items.all()
            ]
            rows.append({
                "kind": "sale",
                "id": f"sale-{s.id}",
                "date": s.created_at,
                "reference": s.receipt_number or f"OR-{s.id}",
                "type": "POS",
                "description": ", ".join(lines) or None,
                "method": s.payment_method,
                "amount": float(s.amount_paid or 0),
                "status": s.payment_status or "paid",
            })

        for t in Tuition.objects.filter(student_id=student_id):
            rows.append({
                "kind": "tuition",
                "id": f"tuition-{t.id}",
                "date": t.payment_date or t.date,
                "reference": t.reference_number or f"RCT-{t.id}",
                "type": "Tuition",
                "description": (t.notes or t.remarks or "").strip() or None,
                "method": t.payment_method or t.method,
                "amount": float(t.amount or 0),
                "status": "paid",
            })

        # Mixed date types (datetime vs date) - normalise to ISO strings, newest first.
        def sort_key(r):
            d = r["date"]
            if d is None:
                return ""
            return d.isoformat()

        rows.sort(key=sort_key, reverse=True)

        return Response({
            "student": {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}".strip(),
                "lrn": getattr(student, "lrn", "") or "",
            },
            "transactions": rows,
            "totals": {
                "count": len(rows),
                "collected": round(sum(r["amount"] for r in rows), 2),
            },
        })

    def get_serializer_class(self):
        from .serializers import PaymentSerializer
        return PaymentSerializer


class StudentChargeViewSet(viewsets.ModelViewSet):
    """Outstanding per-item balances (created when the cashier takes a partial payment)."""

    serializer_class = StudentChargeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from payments.models import StudentCharge as Charge

        queryset = Charge.objects.select_related("student").order_by("-created_at")

        status_filter = self.request.query_params.get("status")
        source = self.request.query_params.get("source")
        student_id = self.request.query_params.get("student")
        outstanding = self.request.query_params.get("outstanding", "").lower() == "true"

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if source:
            queryset = queryset.filter(source=source)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if outstanding:
            queryset = queryset.exclude(status="paid")
        return queryset

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        """Settle (part of) a charge and record the matching Payment."""
        from decimal import Decimal, InvalidOperation
        from payments.models import StudentCharge as Charge, Payment

        charge = self.get_object()

        raw = request.data.get("amount")
        if raw in (None, ""):
            return Response(
                {"error": "amount is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            amount = Decimal(str(raw))
        except (InvalidOperation, TypeError):
            return Response(
                {"error": "amount must be a number"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount <= 0:
            return Response(
                {"error": "amount must be greater than 0"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if amount > charge.balance:
            return Response(
                {
                    "error": f"amount exceeds the remaining balance of {charge.balance}",
                    "balance": str(charge.balance),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        method = request.data.get("payment_method") or "Cash"
        Payment.objects.create(
            student=charge.student,
            amount=amount,
            payment_method=method,
            payment_type=charge.item_name,
            status="completed",
            remarks=f"Settlement: {charge.item_name} x{charge.qty}",
            reference_number=request.data.get("reference_number") or None,
        )

        charge.amount_paid = (charge.amount_paid or 0) + amount
        charge.recompute_status()
        charge.save(update_fields=["amount_paid", "status", "updated_at"])

        return Response(
            {
                "success": True,
                "message": f"Recorded {amount} against {charge.item_name}",
                "charge": self.get_serializer(charge).data,
                "balance": str(charge.balance),
            }
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Outstanding totals per student, split by source.

        grand = tuition_balance + item balances. Tuition-source charges are
        excluded from the grand total because Student.tuition_balance already
        reflects money taken against tuition, so counting both would double it.
        """
        from django.db.models import Sum
        from django.db.models.functions import Coalesce
        from payments.models import StudentCharge as Charge

        rows = (
            Charge.objects.exclude(status="paid")
            .values("student_id")
            .annotate(item_balance=Coalesce(Sum("unit_price"), 0))
        )
        # Amounts need per-row qty * unit_price - amount_paid, so compute in Python.
        per_student = {}
        for c in Charge.objects.exclude(status="paid").select_related("student"):
            entry = per_student.setdefault(
                c.student_id,
                {
                    "student_id": c.student_id,
                    "student_name": f"{c.student.first_name} {c.student.last_name}".strip(),
                    "lrn": c.student.lrn,
                    "item_balance": 0,
                    "tuition_charge_balance": 0,
                    "item_count": 0,
                    "items": [],
                },
            )
            entry["items"].append(
                {
                    "id": c.id,
                    "item_name": c.item_name,
                    "qty": c.qty,
                    "unit_price": str(c.unit_price),
                    "amount_paid": str(c.amount_paid),
                    "balance": str(c.balance),
                    "source": c.source,
                }
            )
            entry["item_count"] += 1
            if c.source == "tuition":
                entry["tuition_charge_balance"] += c.balance
            else:
                entry["item_balance"] += c.balance

        return Response(
            {
                "students": list(per_student.values()),
                "note": (
                    "grand_total = Student.tuition_balance + item_balance; "
                    "tuition_charge_balance is informational only."
                ),
            }
        )
