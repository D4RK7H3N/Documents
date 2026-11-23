from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.throttling import AnonRateThrottle
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Count, Max, DecimalField, Value
from django.db.models.functions import Lower, Coalesce
from django.db import IntegrityError
from uuid import uuid4
from django.shortcuts import get_object_or_404
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from importlib import import_module
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
import logging
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)
from openpyxl import load_workbook
import csv
import os
import io

from students.models import Student, StudentDocument, StudentData
from staff.models import StaffProfile
from dorm.models import DormBuilding, DormRoom, DormAssignment, DormPayment
from sales.models import Sale, SaleItem, Terminal, Disbursement, DailyCashReport
from products.models import Product
from tuition.models import TuitionPayment
from assessment.models import AssessmentType, StudentAssessment, AssessmentPayment
from tours.models import EducationalTour, TourEnrollment, TourPayment
from graduation.models import GraduationEvent, StudentGraduation, GraduationPayment
from payments.models import Payment
from tracks.models import Adviser, Strand, Course, Section
from school_pos.middleware import resolve_terminal


def _canonical_grade_level(raw, level_type, shs_grade, college_year):
    """Normalise a year-level cell to the values the app uses.

    The enrollment sheet writes things like "1st Year", "1st Year Tesda
    Accredited" or "Grade 11"; the app's own dropdowns use "Grade 11",
    "Grade 12", "1st Year Bundled" and "2nd Year Bundled".
    Without this an imported student lands in no year-level bucket at all.
    """
    text = (raw or "").strip()
    low = text.lower()
    if not low:
        return ""
    if low in ("graduated", "graduate", "grad"):
        return "Graduated"
    if level_type == "SHS":
        if "12" in low:
            return "Grade 12"
        if "11" in low:
            return "Grade 11"
        return text
    if level_type == "BUN":
        # The same wording the dropdowns use, so an imported student lands in
        # the same bucket as one added by hand.
        if low.startswith("2") or "second" in low:
            return "2nd Year Bundled"
        if low.startswith("1") or "first" in low:
            return "1st Year Bundled"
        return text
    return text


def _canonical_level_type(raw, grade_level):
    """Normalise the level type, deriving it from the year level when the
    sheet has no Level Type column (a 1st Year row is a Bundled row)."""
    value = (raw or "").strip().upper().replace(" ", "")
    if value in ("SHS", "SH", "SENIORHIGHSCHOOL", "SENIORHIGH"):
        return "SHS"
    if value in ("BUN", "BUNDLED", "TESDA", "TVL"):
        return "BUN"
    if value in ("COL", "COLLEGE"):
        return "COL"
    low = (grade_level or "").strip().lower()
    if "grade" in low:
        return "SHS"
    if "bundled" in low or "tesda" in low or "year" in low:
        return "BUN"
    if "college" in low:
        return "COL"
    return "SHS"


def _clean_lrn(value):
    """Turn the school's LRN into 12 plain digits.

    Their sheets were exported from Excel, so a 12-digit LRN can arrive as a
    float in scientific notation ("1.177E+11") and with stray separators.
    A number in scientific notation is a ROUNDED number - Excel threw away
    the digits - so it is not a usable LRN and comes back empty.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if "e" in text.lower() and "+" in text:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    # A number typed as text in Excel keeps a stray quote ("117414100000'").
    text = text.strip("'").replace(",", "").replace(" ", "").strip()
    # The school writes "NA" where there is no number yet.
    if text.upper() in ("NA", "N/A", "NONE", "NULL", "NIL", "TBD", "?"):
        return ""
    return text


def _placeholder_lrn(last_name, first_name, dob):
    """A stable stand-in LRN for a sheet row that has none.

    Some of the school's files have no LRN column at all, and their CSV
    exports lost the digits to Excel's rounding. A student still has to reach
    the roster, so a placeholder is made from the name and the date of
    birth: the same student always gets the same number, so re-importing
    the file updates that student instead of creating a duplicate.
    """
    import hashlib

    key = "%s|%s|%s" % (
        (last_name or "").strip().lower(),
        (first_name or "").strip().lower(),
        (dob or "").strip().lower(),
    )
    digits = hashlib.sha1(key.encode("utf-8")).hexdigest()
    number = int(digits[:11], 16) % 10 ** 11
    return "0%011d" % number


def _pick_section(level_type, grade_year, strand_obj, course_obj, counts):
    """The section of this year level that teaches the sheet's strand (SHS)
    or course (Bundled), or None when the school has not created one.

    The sections are configured with their strand, so a sheet that only names
    the strand can still be placed. The section with the fewest students
    takes the next one so the classes stay even; the name breaks a tie.
    """
    queryset = Section.objects.filter(level_type=level_type, grade_year=grade_year)
    if strand_obj is not None:
        queryset = queryset.filter(strand_id=strand_obj.id)
    elif course_obj is not None:
        queryset = queryset.filter(course_id=course_obj.id)
    else:
        return None
    candidates = list(queryset.order_by("name"))
    if not candidates:
        return None

    def student_count(name):
        if name not in counts:
            counts[name] = Student.objects.filter(section=name).count()
        return counts[name]

    return min(candidates, key=lambda s: (student_count(s.name), s.name)).name


def _match_strand(value):
    """The school's strand for a wording used in an enrollment sheet.

    A strand is named by its own name, by its code or by one of the
    alternative names the admin recorded for it (the DepEd programme names
    the school knows them by).
    """
    text = (value or "").strip()
    if not text:
        return None
    strand = (
        Strand.objects.filter(name__iexact=text).first()
        or Strand.objects.filter(code__iexact=text).first()
    )
    if strand:
        return strand
    for candidate in Strand.objects.exclude(aliases__isnull=True).exclude(aliases=""):
        names = [
            a.strip().lower()
            for a in (candidate.aliases or "").split(",")
            if a.strip()
        ]
        if text.lower() in names:
            return candidate
    return None


def _match_course(value):
    """The school's course for a wording used in an enrollment sheet."""
    text = (value or "").strip()
    if not text:
        return None
    course = (
        Course.objects.filter(name__iexact=text).first()
        or Course.objects.filter(code__iexact=text).first()
    )
    if course:
        return course
    for candidate in Course.objects.exclude(aliases__isnull=True).exclude(aliases=""):
        names = [
            a.strip().lower()
            for a in (candidate.aliases or "").split(",")
            if a.strip()
        ]
        if text.lower() in names:
            return candidate
    return None


def _sections_named_in_file(file_name):
    """The sections a class list is named after.

    The school's sheets are named after their class
    ("G-11-THESSALONIANS-FBS.csv", "ATS_1B_bundle_.xlsx", "HRS1B.csv"), so
    the file name says which class the rows belong to. The comparison
    ignores the separators, so "HRS 1B" is found in "HRS1B.csv" and
    "ATS 1A" in "ATS 1-Anew.xls".
    """
    stem = os.path.splitext(os.path.basename(file_name or ""))[0].upper()
    compact = "".join(ch for ch in stem if ch.isalnum())
    if not compact:
        return []
    found = []
    for candidate in Section.objects.all().order_by("name"):
        name = (candidate.name or "").strip()
        key = "".join(ch for ch in name.upper() if ch.isalnum())
        if len(key) < 3 or key not in compact:
            continue
        found.append((compact.index(key), -len(key), name))
    # The earliest match wins: "G11- PROVERBS AMOS.xlsx" names two classes
    # and the first one is the class of the sheet.
    found.sort()
    return [name for _, _, name in found]


def _parse_dob(value):
    """Parse a date-of-birth cell into a date.

    Excel hands back real dates for date-formatted cells and strings for
    everything else, so both are handled. Unparseable values return None
    instead of failing the whole row.
    """
    if not value:
        return None
    if hasattr(value, "year"):
        return value.date() if hasattr(value, "date") else value
    text = str(value).strip()
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%Y/%m/%d",
        "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y",
        # A cell that Excel already formatted as a date and that reached the
        # importer as text ("2008-04-21 00:00:00").
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
        # The other ways the school's sheets write a date.
        "%d-%b-%y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y", "%b. %d, %Y",
        "%m/%d.%Y", "%m-%d-%Y", "%d.%m.%Y",
    ):
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        if parsed > date.today():
            # A birth date cannot be in the future - the sheet wrote the year
            # wrong (a two digit year, "16/1/26"). The date is left empty
            # instead of being stored wrong.
            return None
        return parsed
    # A stray space inside the date ("04/24/ 2008").
    tight = "".join(text.split())
    if tight != text:
        return _parse_dob(tight)
    return None


def _current_school_year():
    """The school's configured academic year (e.g. "2026-2027") or None."""
    from school_config.models import SchoolConfiguration

    cfg = SchoolConfiguration.objects.first()
    return (cfg.current_academic_year or "").strip() if cfg else ""


def _sync_grade_label(student):
    """Recompute current_grade_level from the raw grade columns.

    The label is what the roster, the class lists and the import all read,
    so it has to follow the year level - whichever way that was changed.
    """
    if student.level_type == "SHS":
        if student.shs_grade == "12":
            student.current_grade_level = "Grade 12"
        elif student.shs_grade == "11":
            student.current_grade_level = "Grade 11"
        elif student.shs_grade:
            student.current_grade_level = f"Grade {student.shs_grade}"
        else:
            student.current_grade_level = student.current_grade_level or "N/A"
    elif student.level_type in ("BUN", "COL"):
        if student.college_year == "1":
            student.current_grade_level = (
                "1st Year Bundled"
                if student.level_type == "BUN"
                else "College 1st Year"
            )
        elif student.college_year == "2":
            student.current_grade_level = (
                "2nd Year Bundled"
                if student.level_type == "BUN"
                else "College 2nd Year"
            )
        elif student.college_year in ("3", "4"):
            ordinal = "3rd" if student.college_year == "3" else "4th"
            student.current_grade_level = f"College {ordinal} Year"
    return student.current_grade_level


def _apply_section_placement(student, section_obj):
    """Put a student in a section the way that section defines it.

    A section has one strand and one year level, so a student who transfers
    to another section has to move with it. Before this, a transfer could
    leave the roster saying the student is in the Automotive section while
    their strand still said Electronics - and the class list and the SOA
    then disagreed with each other.

    Returns True when something was changed.
    """
    import re as _re

    if section_obj is None:
        return False

    changed = False

    if section_obj.strand_id:
        if student.strand_id != section_obj.strand_id:
            changed = True
        student.strand = section_obj.strand
        student.track_strand = section_obj.strand.name

    if section_obj.level_type and student.level_type != section_obj.level_type:
        student.level_type = section_obj.level_type
        changed = True

    grade = (section_obj.grade_year or "").strip()
    match = _re.search(r"(\d+)", grade)
    if match:
        num = match.group(1)
        if _re.search(r"year", grade, _re.IGNORECASE):
            if student.college_year != num:
                changed = True
            student.college_year = num
            if student.level_type == "SHS" and student.shs_grade is not None:
                student.shs_grade = None
                changed = True
        else:
            if student.shs_grade != num:
                changed = True
            student.shs_grade = num
            if student.level_type in ("BUN", "COL") and student.college_year is not None:
                student.college_year = None
                changed = True

    return changed


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
    TerminalSerializer,
    AdviserSerializer,
    DisbursementSerializer,
    DailyCashReportSerializer,
)


from school_pos.throttling import LoginRateThrottle
from school_pos.permissions import IsSuperUser, SuperUserDeleteMixin


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


# Live progress of running bulk imports, keyed by the progress id the client
# generated. Waitress serves requests on a small thread pool inside one
# process, so the polling GET reads what the importing POST writes here.
_BULK_IMPORT_PROGRESS = {}


class StudentViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
    """Student CRUD operations"""

    queryset = Student.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Alphabetical, like a school roster. A case-insensitive sort so a
        # surname that starts with a small letter still lands with its
        # neighbours, and -id as the final tiebreaker so PageNumberPagination
        # cannot return inconsistent pages (it warns and can repeat or skip
        # rows on an unordered queryset).
        #
        # The totals are annotated and the relations pulled in with one query
        # each: the serializer used to run four extra queries PER STUDENT, so
        # a 700-student roster cost about 3,000 queries and seven seconds.
        queryset = (
            Student.objects.all()
            .select_related("strand__track", "enrollment_data", "course_fk")
            .annotate(
                _total_paid=Coalesce(
                    Sum("tuition_payments__amount"),
                    Value(Decimal("0")),
                    output_field=DecimalField(),
                ),
                _last_tuition_date=Max("tuition_payments__date"),
                _last_payment_date=Max("payments__created_at"),
            )
            .order_by(
                Lower("last_name"), Lower("first_name"), Lower("middle_name"), "-id"
            )
        )

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
        old_section = (instance.section or "").strip()

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

        # A student who moves to another section moves with that section's
        # strand and year level. The edit form always sends the grade it
        # happens to show, so the section decides whenever the section
        # changed - otherwise a transfer could leave the roster and the
        # strand contradicting each other.
        new_section = (student.section or "").strip()
        if new_section and new_section != old_section:
            from tracks.models import Section as SectionModel

            section_obj = SectionModel.objects.filter(name=new_section).first()
            if section_obj is not None:
                _apply_section_placement(student, section_obj)
                _sync_grade_label(student)
                from django.utils import timezone as _tz

                student.section_assigned_by = (
                    self.request.user.get_full_name()
                    or getattr(self.request.user, "username", "")
                    or None
                )
                student.section_assigned_at = _tz.now()
                student.save(
                    update_fields=[
                        "strand",
                        "track_strand",
                        "level_type",
                        "shs_grade",
                        "college_year",
                        "current_grade_level",
                        "section_assigned_by",
                        "section_assigned_at",
                    ]
                )
                new_shs_grade = student.shs_grade
                new_college_year = student.college_year

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
                    student.current_grade_level = "1st Year Bundled" if student.level_type == "BUN" else "College 1st Year"
                elif new_college_year == "2":
                    student.current_grade_level = "2nd Year Bundled" if student.level_type == "BUN" else "College 2nd Year"
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
                    "1st Year Bundled" if old_college_year == "1" else
                    "2nd Year Bundled" if old_college_year == "2" else
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

        # The track/strand above only selects WHICH students move. The target
        # section then decides their strand and year level - it has one of
        # each, and a section whose strand contradicts its students is the
        # thing the class lists and the SOA read from.
        target_obj = None
        try:
            from tracks.models import Section as SectionModel

            target_obj = SectionModel.objects.filter(name=target_section).first()
        except Exception:
            target_obj = None

        # What to write into the free-text Student.track_strand column. Prefer
        # the target section's strand, then the strand that was selected.
        strand_label = ""
        if target_obj is not None and target_obj.strand_id:
            strand_label = target_obj.strand.name
        elif strand:
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
        if target_obj is not None and target_obj.strand_id:
            acceptable_labels.update({target_obj.strand.name, target_obj.strand.code})

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
                    and (
                        target_obj is None
                        or not target_obj.strand_id
                        or student.strand_id == target_obj.strand_id
                    )
                ):
                    continue
                student.section = target_section
                if target_obj is not None:
                    _apply_section_placement(student, target_obj)
                    _sync_grade_label(student)
                student.track_strand = strand_label
                if target_obj is None and strand_obj is not None:
                    student.strand = strand_obj
                student.section_assigned_by = actor
                student.section_assigned_at = now
                student.save(
                    update_fields=[
                        "section",
                        "track_strand",
                        "strand",
                        "level_type",
                        "shs_grade",
                        "college_year",
                        "current_grade_level",
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

        # Unpaid assessment fees are payable at the register just like any
        # other charge, so the cashier can settle them together with tuition.
        from assessment.models import StudentAssessment as _StudentAssessment

        assessment_rows = (
            _StudentAssessment.objects.filter(student=student, balance__gt=0)
            .select_related("assessment_type")
            .order_by("id")
        )
        unpaid_assessments = [
            {
                "id": a.id,
                "name": a.assessment_type.name,
                "code": a.assessment_type.code,
                "total_fee": float(a.total_fee or 0),
                "amount_paid": float(a.amount_paid or 0),
                "balance": float(a.balance or 0),
                "status": a.status,
            }
            for a in assessment_rows
        ]
        assessment_balance = round(
            sum(a["balance"] for a in unpaid_assessments), 2
        )
        outstanding = round(outstanding + assessment_balance, 2)

        # Per-term tuition breakdown, so the cashier can show what the fee
        # is made of without opening another page. OneToOne, so it is simply
        # absent for students who have no breakdown row yet.
        breakdown_payload = None
        try:
            bd = student.tuition_breakdown
            breakdown_payload = {
                "academic_year": bd.academic_year,
                "terms": [
                    {"label": "1st Term", "amount": float(bd.first_term or 0)},
                    {"label": "2nd Term", "amount": float(bd.second_term or 0)},
                    {"label": "3rd Term", "amount": float(bd.third_term or 0)},
                    {"label": "Final Term", "amount": float(bd.final_term or 0)},
                ],
                "total": float(bd.total),
            }
        except ObjectDoesNotExist:
            pass

        serializer = StudentSerializer(student, context={"request": request})
        return Response({
            "student": serializer.data,
            "unpaid_charges": charges,
            "unpaid_assessments": unpaid_assessments,
            "tuition_breakdown": breakdown_payload,
            "totals": {
                "item_total": round(item_total, 2),
                # Authoritative tuition due (fee - paid from the rows), not the
                # raw cache - see the comment above.
                "tuition_balance": tuition_due,
                "assessment_balance": assessment_balance,
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
                # How many students are enrolled at all. Without it the page
                # cannot tell "there is nobody to promote" apart from
                # "everybody is already at their current year level".
                "total_enrolled": Student.objects.filter(
                    not_dropped_out, not_inactive
                ).count(),
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

        # A promoted student must move into a section of the NEW year level
        # that teaches the same strand (SHS) or the same course (Bundled).
        # Leaving them in the old section leaves the roster saying
        # "Grade 12" inside a Grade 11 class - and the section decides where
        # the student belongs, so it has to follow.
        section_counts = {}

        def student_count(name):
            if name not in section_counts:
                section_counts[name] = Student.objects.filter(section=name).count()
            return section_counts[name]

        def target_section(student, level_type, grade_year):
            """The section of the new year level for this student's strand or
            course, or None when the school has not created one yet.

            The strand normally lives on the SECTION, not on the student
            row - the section is the authority - so the current section is
            consulted when the student carries no strand of their own.
            """
            current = Section.objects.filter(name=(student.section or "").strip()).first()
            strand_id = student.strand_id or (current.strand_id if current else None)
            course_id = student.course_fk_id or (current.course_id if current else None)

            queryset = Section.objects.filter(
                level_type=level_type, grade_year=grade_year
            )
            if level_type == "BUN" and course_id:
                # A bundled student is identified by the course.
                queryset = queryset.filter(course_id=course_id)
            elif strand_id:
                queryset = queryset.filter(strand_id=strand_id)
            elif course_id:
                queryset = queryset.filter(course_id=course_id)
            else:
                return None
            candidates = list(queryset.order_by("name"))
            if not candidates:
                return None
            # Keep the classes even: the section with the fewest students
            # takes the next one. The name breaks a tie, so the result is
            # the same every time.
            return min(candidates, key=lambda s: (student_count(s.name), s.name)).name

        unplaced = []

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
                # Take the graduates FIRST. A student promoted from Grade 11
                # to Grade 12 in this run must not be graduated in the same
                # run - they would skip a whole year.
                grade_12_students = list(
                    prepare(
                        scoped(
                            Student.objects.filter(
                                Q(level_type="SHS", shs_grade="12")
                                | Q(current_grade_level="Grade 12"),
                            )
                        )
                    )
                )
                grade_11_students = list(
                    prepare(
                        scoped(
                            Student.objects.filter(
                                Q(level_type="SHS", shs_grade="11")
                                | Q(current_grade_level="Grade 11"),
                            )
                        )
                    )
                )

                for student in grade_11_students:
                    student.level_type = "SHS"
                    student.shs_grade = "12"
                    student.current_grade_level = "Grade 12"
                    student.enrollment_status = "Continuing"

                    target = target_section(student, "SHS", "Grade 12")
                    if target:
                        if student.section != target:
                            section_counts.pop(student.section, None)
                            student.section = target
                            section_counts[target] = section_counts.get(target, 0) + 1
                        # The section is the authority on the strand, so the
                        # student takes the new section's strand with them.
                        placed = Section.objects.filter(name=target).first()
                        if placed:
                            student.strand_id = placed.strand_id
                            student.course_fk_id = placed.course_id
                    else:
                        unplaced.append(
                            {
                                "name": f"{student.first_name} {student.last_name}",
                                "reason": "no Grade 12 section for this strand",
                                "section": student.section,
                            }
                        )

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

                # The graduates were taken before the promotion above, so a
                # student who was just moved to Grade 12 is NOT among them.
                for student in grade_12_students:
                    student.level_type = "SHS"
                    student.shs_grade = "12"
                    student.enrollment_status = "Graduated"
                    student.current_grade_level = "Graduated"
                    student.status = "Graduated"
                    student.graduated_sy = _current_school_year() or None
                    student.save()
                    graduated_count += 1

            if promote_type in ["bundled", "all"]:
                # Same rule as the SHS branch: the graduates are taken first,
                # so a student moved from 1st to 2nd Year is not graduated in
                # the same run.
                year_2_students = list(
                    prepare(
                        scoped(
                            Student.objects.filter(
                                Q(level_type="BUN", college_year="2")
                                | Q(current_grade_level="2nd Year Bundled")
                                | Q(current_grade_level="2nd Year Tesda Accredited"),
                            )
                        )
                    )
                )
                year_1_students = list(
                    prepare(
                        scoped(
                            Student.objects.filter(
                                Q(level_type="BUN", college_year="1")
                                | Q(current_grade_level="1st Year Bundled")
                                | Q(current_grade_level="1st Year Tesda Accredited"),
                            )
                        )
                    )
                )

                for student in year_1_students:
                    student.level_type = "BUN"
                    student.college_year = "2"
                    student.current_grade_level = "2nd Year Bundled"
                    student.enrollment_status = "Continuing"

                    target = target_section(student, "BUN", "2nd Year")
                    if target:
                        if student.section != target:
                            section_counts.pop(student.section, None)
                            student.section = target
                            section_counts[target] = section_counts.get(target, 0) + 1
                        placed = Section.objects.filter(name=target).first()
                        if placed:
                            student.strand_id = placed.strand_id
                            student.course_fk_id = placed.course_id
                    else:
                        unplaced.append(
                            {
                                "name": f"{student.first_name} {student.last_name}",
                                "reason": "no 2nd Year section for this course",
                                "section": student.section,
                            }
                        )

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

                # The graduates were taken before the promotion above.
                for student in year_2_students:
                    student.level_type = "BUN"
                    student.college_year = "2"
                    student.enrollment_status = "Graduated"
                    student.current_grade_level = "Graduated"
                    student.status = "Graduated"
                    student.graduated_sy = _current_school_year() or None
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
                    # Students who were promoted but could not be placed in a
                    # section of the new year level - the school has to
                    # create that section first.
                    "unplaced": unplaced,
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

        file_name = (file.name or "").lower()
        if not file_name.endswith((".xlsx", ".xls", ".csv")):
            return Response(
                {
                    "success": False,
                    "error": "Please upload an .xlsx, .xls or .csv file.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Load the sheet into plain rows. The school sends .xlsx, .xls
            # AND .csv files, so all three have to work.
            payload = file.read()
            rows = []
            if file_name.endswith(".xlsx"):
                workbook = load_workbook(io.BytesIO(payload))
                # Try to get the "Student Data Enrollment" sheet, fallback to active sheet
                if "Student Data Enrollment" in workbook.sheetnames:
                    sheet = workbook["Student Data Enrollment"]
                else:
                    sheet = workbook.active
                for row in sheet.iter_rows(values_only=True):
                    rows.append(list(row))
            elif file_name.endswith(".xls"):
                import xlrd

                book = xlrd.open_workbook(file_contents=payload)
                sheet = book.sheet_by_index(0)
                for r in range(sheet.nrows):
                    row = []
                    for c in range(sheet.ncols):
                        cell = sheet.cell(r, c)
                        if cell.ctype == xlrd.XL_CELL_DATE:
                            # A date cell comes back as a serial number -
                            # turn it back into a date.
                            try:
                                row.append(
                                    xlrd.xldate_as_datetime(
                                        cell.value, book.datemode
                                    )
                                )
                                continue
                            except Exception:
                                pass
                        if (
                            cell.ctype == xlrd.XL_CELL_NUMBER
                            and float(cell.value).is_integer()
                        ):
                            # A phone number or a number typed into the sheet
                            # must not keep its ".0".
                            row.append(int(cell.value))
                            continue
                        row.append(cell.value)
                    rows.append(row)
            else:
                # The school exports the sheets from Excel on Windows, and
                # those files are written in the system's own encoding
                # (Windows-1252): a name like "Broñosa" must not come out as
                # "Bro?osa".
                try:
                    text = payload.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = payload.decode("cp1252", errors="replace")
                rows = [list(r) for r in csv.reader(io.StringIO(text))]

            if not rows:
                return Response(
                    {"success": False, "error": "The file is empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get headers from first row.
            # A blank heading still occupies its column, so it is kept as an
            # empty name - dropping it would shift every following column and
            # the row would be read one column to the left.
            headers = []
            for value in rows[0]:
                if value in (None, ""):
                    headers.append("")
                else:
                    headers.append(str(value).strip().lower())

            if not any(headers):
                return Response(
                    {"success": False, "error": "No headers found in the first row"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ---- work out which column is which ----------------------------
            # Schools name the same column differently ("Section",
            # "Section Name", "Sec", "Block"...), and a column that is not
            # recognised is silently ignored - the students then land with no
            # section at all. Headers are therefore matched on a normalised
            # form (letters and digits only) and, when several columns could
            # serve the same field, the one that comes FIRST in the sheet
            # wins: the enrollment sheet puts the student's columns before the
            # guardian's, so "Address" (student) and the second "Address"
            # (guardian) are told apart by their position, not by name.
            def _norm_header(value):
                return "".join(
                    ch for ch in str(value).strip().lower() if ch.isalnum()
                )

            header_list = list(headers)
            norm_first = {}
            for index, header in enumerate(header_list):
                norm_first.setdefault(_norm_header(header), index)

            def _row_key(index):
                """The key this column ends up under in row_data. Repeated
                headers are suffixed ("address__2")."""
                original = header_list[index]
                seen = sum(1 for h in header_list[:index] if h == original)
                return original if seen == 0 else f"{original}__{seen + 1}"

            def _match(aliases, needles=()):
                found = []
                for alias in aliases:
                    index = norm_first.get(alias)
                    if index is not None and index not in found:
                        found.append(index)
                for norm_key, index in norm_first.items():
                    if any(n in norm_key for n in needles) and index not in found:
                        found.append(index)
                return sorted(found)

            def _pick(aliases, needles=(), after=None, occurrence=0):
                """The column for a field. With `after`, only columns further
                right than that index are considered (the guardian's copy of
                a repeated column)."""
                found = _match(aliases, needles)
                if after is not None:
                    later = [i for i in found if i > after]
                    if later:
                        found = later
                if not found:
                    return None
                index = found[min(occurrence, len(found) - 1)]
                return _row_key(index)

            header_aliases = {
                "lrn": ("lrn", "lrnnumber", "lrnno",
                        "learnerreferencenumber", "studentid", "studentnumber",
                        "idnumber"),
                "first_name": ("firstname", "first", "fname", "givenname"),
                "middle_name": ("middlename", "middle", "mname"),
                "last_name": ("lastname", "last", "lname", "surname",
                              "familyname"),
                "student_name": ("studentname", "name", "fullname"),
                "gender": ("gender", "sex"),
                "address": ("homeaddress", "studentaddress", "address"),
                "dob": ("dob", "dateofbirth", "birthday", "birthdate", "bd"),
                "contact_number": ("contactnumber", "contactno", "contact",
                                   "phone", "phonenumber", "cellphone",
                                   "cellnumber", "mobile"),
                "guardian_name": ("guardian", "guardianname", "guardianparent",
                                  "guardianparentname", "parent"),
                "strand": ("strand", "strands", "strandcourse", "trackstrand",
                           "track", "trackstrands", "specialization", "program"),
                "course": ("course", "courses", "coursecodename"),
                "section": ("section", "sectionname", "sec", "block",
                            "class", "classname", "sectionassignment",
                            "sectioncode", "homeroom"),
                "grade_level": ("gradelevel", "grade", "yearlevel", "year",
                                "level", "shsgrade", "collegeyear",
                                "gradeyear", "gradeandyear"),
                "school_year": ("schoolyear", "academicyear", "sy", "sydescription"),
                "tuition": ("tuition", "tuitionfee", "tuitionbalance",
                            "tuitionamount"),
                "amount_paid": ("amountpaid", "tuitionpaid", "paid", "paidamount"),
                "payment_method": ("paymentmethod", "method"),
            }
            header_substrings = {
                "section": ("section", "block", "class"),
                "strand": ("strand", "track"),
                "course": ("course",),
                "grade_level": ("grade", "year", "level"),
                "tuition": ("tuition",),
                "amount_paid": ("paid",),
                "school_year": ("schoolyear", "academicyear"),
                "address": ("address",),
                "contact_number": ("contact", "phone", "mobile"),
            }

            hmap = {}
            for field, aliases in header_aliases.items():
                key = _pick(aliases, header_substrings.get(field, ()))
                if key:
                    hmap[field] = key

            # The guardian's copy of the address / contact columns is the one
            # AFTER the student's.
            address_index = norm_first.get(_norm_header(hmap.get("address", "")))
            hmap["guardian_address"] = _pick(
                ("guardianaddress", "guardianparentaddress"),
                ("address",),
                after=address_index,
            )
            contact_index = norm_first.get(_norm_header(hmap.get("contact_number", "")))
            hmap["guardian_contact"] = _pick(
                ("guardiancontact", "guardiancontactnumber",
                 "guardianparentcontact", "guardianphone", "parentcontact"),
                ("contact", "phone", "mobile"),
                after=contact_index,
            )

            def _cell(row, field, *legacy):
                """Value for a field: the detected column first, then any
                legacy alias, then empty."""
                key = hmap.get(field)
                if key and key in row:
                    value = row.get(key)
                    if value not in (None, ""):
                        return value
                for alias in legacy:
                    value = row.get(alias)
                    if value not in (None, ""):
                        return value
                return ""

            created_count = 0
            updated_count = 0
            errors = []
            skipped_count = 0
            sections_created = 0
            sections_updated = 0
            warnings = []
            rows_with_section = 0
            # Rows that arrived without a Section column and were placed into
            # a section from the strand their sheet names.
            rows_placed_by_strand = 0
            rows_placed_by_strand_list = []
            # Rows that were placed into the class their FILE NAME says
            # ("ATS 1A", "HRS 1B", "Thessalonians").
            rows_placed_by_file = 0
            # Rows whose LRN was missing (or lost to Excel's rounding) and
            # got a stable placeholder instead.
            placeholder_lrns = 0
            # Students whose placeholder number was replaced by the real LRN
            # when the school sent the sheet again with the numbers in it.
            placeholder_upgraded = 0
            # The school lists some students twice in one sheet - the same
            # person on two lines. This remembers who was already read.
            seen_students = {}
            merged_duplicates = 0
            section_counts = {}
            # The school's sheets have no Section column - the class is in the
            # FILE NAME ("G-11-THESSALONIANS-FBS.csv"). The sections whose
            # name appears in it are collected here, in the order they appear.
            try:
                file_sections = _sections_named_in_file(file.name or "")
            except Exception:
                file_sections = []
            file_section_objs = []
            if file_sections:
                found = {
                    section.name: section
                    for section in Section.objects.filter(name__in=file_sections)
                }
                file_section_objs = [
                    found[name] for name in file_sections if name in found
                ]
            rows_without_section = []
            unmapped_strands = {}
            strands_inherited = 0

            # Live progress for the loading screen: the browser keeps polling
            # import_progress/ with this id while the import request runs.
            progress_id = str(request.data.get("progress_id") or "").strip()
            total_rows = max(0, len(rows) - 1)
            if progress_id:
                # Keep the store bounded - only the recent imports matter.
                while len(_BULK_IMPORT_PROGRESS) >= 40:
                    _BULK_IMPORT_PROGRESS.pop(next(iter(_BULK_IMPORT_PROGRESS)), None)
                _BULK_IMPORT_PROGRESS[progress_id] = {
                    "total": total_rows,
                    "done": 0,
                    "finished": False,
                    "summary": None,
                }

            for row_num, row in enumerate(rows[1:], start=2):
                try:
                    row_data = {}
                    for idx, header in enumerate(headers):
                        if not header:
                            # A blank heading has no field of its own, but its
                            # column still holds a value - skip the name, keep
                            # the column.
                            continue
                        if idx < len(row):
                            cell_value = row[idx]
                            # The sheet repeats a few headers ("Address" and
                            # "Contact Number" appear for the student AND the
                            # guardian). Keep the first under the plain key and
                            # the next ones under "header__2", "header__3", so
                            # neither is lost.
                            key = header
                            if key in row_data:
                                suffix = 2
                                while f"{header}__{suffix}" in row_data:
                                    suffix += 1
                                key = f"{header}__{suffix}"
                            row_data[key] = (
                                cell_value if cell_value is not None else ""
                            )

                    # Extract fields - support multiple header variations
                    # Debug: Print first row's data to help diagnose issues
                    if row_num == 2 and not errors:
                        logger.debug(
                            "import row 2 header sample: %s", list(row_data.keys())[:5]
                        )

                    lrn = _clean_lrn(
                        _cell(row_data, "lrn", "lrn", "lrn number", "student_id")
                    )
                    first_name = str(_cell(row_data, "first_name", "firstname", "first name")).strip()
                    last_name = str(_cell(row_data, "last_name", "lastname", "last name")).strip()
                    middle_name = str(_cell(row_data, "middle_name", "middle", "middlename", "middle name")).strip()
                    grade_level = str(_cell(row_data, "grade_level", "gradelevel", "grade level", "grade/year level", "year level", "grade")).strip()
                    level_type = (
                        str(_cell(row_data, "level_type", "leveltype", "level type (shs/col/bun)", "level"))
                        .strip()
                        .upper()
                    )
                    # The class the sheet is about says which year level it
                    # is: the bundled sheets carry no level column at all
                    # ("ATS 1A", "HRS 1B"), and the section the admin set up
                    # is the authority on it.
                    if file_section_objs:
                        file_section = file_section_objs[0]
                        sheet_level = grade_level.strip().lower()
                        if sheet_level not in ("graduated", "graduate", "grad"):
                            if file_section.level_type:
                                level_type = file_section.level_type
                            if file_section.grade_year:
                                grade_level = file_section.grade_year
                    enrollment_status = str(
                        row_data.get("status", "")
                        or row_data.get("enrollment_status", "")
                        or row_data.get("enrollment status", "")
                        or "New"
                    ).strip()
                    track_strand = str(
                        _cell(row_data, "strand", "track_strand", "track/course code", "strand", "track")
                    ).strip()
                    # The bundled sheets put the qualification in a "Course"
                    # column instead of the strand column. When both columns
                    # are the same one ("Strand/Course Code") the strand
                    # column is used - it is the same value anyway.
                    sheet_course = ""
                    course_key = hmap.get("course")
                    if course_key and course_key != hmap.get("strand"):
                        sheet_course = str(row_data.get(course_key, "") or "").strip()
                    section = str(
                        _cell(row_data, "section", "section", "section name")
                    ).strip()
                    # Contact / address / guardian / demographics columns.
                    # The enrollment sheet carries them; the importer used to
                    # drop them on the floor.
                    address = str(
                        _cell(row_data, "address", "home address", "student address")
                    ).strip()
                    guardian_address = str(
                        _cell(row_data, "guardian_address", "address__2", "guardian address", "guardian/parent address")
                    ).strip()
                    gender = str(_cell(row_data, "gender", "gender", "sex")).strip().title()
                    # Some sheets write just "M" or "F", and one writes
                    # "Famale".
                    if gender in ("M", "F"):
                        gender = "Male" if gender == "M" else "Female"
                    elif gender == "Famale":
                        gender = "Female"
                    dob = str(
                        _cell(row_data, "dob", "dob", "date of birth", "birthday")
                    ).strip()
                    contact_number = str(
                        _cell(row_data, "contact_number", "contact number", "contact no", "contact", "phone", "cellphone")
                    ).strip()
                    guardian_name = str(
                        _cell(row_data, "guardian_name", "guardian", "guardian name", "guardian/parent", "guardian/parent name")
                    ).strip()
                    guardian_contact = str(
                        _cell(row_data, "guardian_contact", "contact number__2", "guardian contact", "guardian contact number", "guardian/parent contact", "guardian phone")
                    ).strip()
                    guardian_address = str(
                        _cell(row_data, "guardian_address", "address__2", "guardian address")
                    ).strip()

                    # Column A of the enrollment sheet is "Student Name" in
                    # "Last, First Middle" form ("Allego, James Ivan Caro").
                    # Used whenever the dedicated name columns are empty.
                    student_name = str(
                        _cell(row_data, "student_name", "student name", "name", "full name")
                    ).strip()
                    if student_name and (not first_name or not last_name):
                        if "," in student_name:
                            last_part, rest = student_name.split(",", 1)
                            parts = rest.strip().split()
                            if parts:
                                first_name = first_name or parts[0]
                                middle_name = middle_name or " ".join(parts[1:])
                            last_name = last_name or last_part.strip()
                        else:
                            parts = student_name.strip().split()
                            if len(parts) >= 2:
                                last_name = last_name or parts[-1]
                                first_name = first_name or parts[0]
                                middle_name = middle_name or " ".join(parts[1:-1])
                            else:
                                first_name = first_name or parts[0]
                    # ---- tuition -------------------------------------------------
                    # An imported student may already carry a fee for a school
                    # year. The sheet can carry it: a "Tuition" column (the
                    # fee for the year) and optionally an "Amount Paid"
                    # column (already collected). Without a Tuition column
                    # nothing is touched - the fee is set later from the Enroll
                    # page or at the cashier.
                    tuition = str(
                        _cell(row_data, "tuition", "tuition", "tuition fee", "tuition balance")
                    ).strip()
                    tuition_paid = str(
                        _cell(row_data, "amount_paid", "amount paid", "tuition paid", "paid")
                    ).strip()
                    row_school_year = str(
                        _cell(row_data, "school_year", "school year", "academic year", "s.y.", "sy")
                    ).strip() or (_current_school_year() or "")

                    # Debug: Print extracted values for first row
                    if row_num == 2 and not errors:
                        logger.debug("import row 2 produced %d fields", len(row_data))

                    # Skip empty rows
                    if not lrn and not last_name and not first_name:
                        skipped_count += 1
                        continue

                    # Some of the school's files have no LRN column at all,
                    # and their CSV exports lost the digits to Excel's
                    # rounding. The student still has to reach the roster,
                    # so a stable placeholder is made from the name and the
                    # date of birth - re-importing the file updates that
                    # student instead of creating a duplicate.
                    used_placeholder = False
                    upgraded_lrn = False
                    if not lrn:
                        lrn = _placeholder_lrn(last_name, first_name, dob)
                        placeholder_lrns += 1
                        used_placeholder = True

                    # Validate required fields
                    if not lrn or not last_name or not first_name:
                        errors.append(
                            f"Row {row_num}: Missing required fields (LRN='{lrn}', FirstName='{first_name}', LastName='{last_name}')"
                        )
                        continue

                    # The section counting happens after the strand lookup
                    # below, where a row without a Section column can still be
                    # placed into a section from its strand.

                    # Validate level type — the sheet often has no Level Type
                    # column, so it is derived from the year level instead of
                    # failing the row.
                    level_type = _canonical_level_type(level_type, grade_level)

                    # Validate enrollment status
                    valid_statuses = ["New", "Continuing", "Transferee", "ALS Graduate"]
                    if enrollment_status not in valid_statuses:
                        enrollment_status = "New"

                    # Tuition: only ever set from an explicit Tuition column.
                    # No auto-calculation from status - the fee structure is not
                    # inferred here, tuition is assigned manually per student
                    # afterwards. Anything unparseable leaves the balance at 0.
                    tuition_fee = None
                    if tuition:
                        try:
                            tuition_fee = Decimal(str(tuition).replace(",", ""))
                        except (InvalidOperation, TypeError, ValueError):
                            warnings.append(
                                f"Row {row_num}: tuition '{tuition}' is not a number - skipped."
                            )
                    tuition_paid_amount = Decimal("0")
                    if tuition_paid:
                        try:
                            tuition_paid_amount = Decimal(
                                str(tuition_paid).replace(",", "")
                            )
                        except (InvalidOperation, TypeError, ValueError):
                            tuition_paid_amount = Decimal("0")
                            warnings.append(
                                f"Row {row_num}: amount paid '{tuition_paid}' is not a number - treated as 0."
                            )
                    tuition_method = str(
                        row_data.get("payment method", "")
                        or row_data.get("payment_method", "")
                        or row_data.get("method", "")
                    ).strip() or "Cash"

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

                    # The year level the app uses. A "Graduated" row is marked as
                    # such so it leaves the working roster and keeps its S.Y.
                    canonical_grade = _canonical_grade_level(
                        grade_level, level_type, shs_grade, college_year
                    )
                    is_graduated_row = canonical_grade == "Graduated"
                    if is_graduated_row:
                        enrollment_status = "Graduated"

                    # A graduated student has left the roster: no year-level
                    # guess, and no section is created for them.
                    if is_graduated_row:
                        shs_grade = None
                        college_year = None

                    # ---- strand / course lookup --------------------------------
                    # The sheet names a strand (STEM, ABM, ...) for SHS rows and
                    # a course for the bundled rows. Match the existing records
                    # by name or code; never invent one behind the admin's back.
                    strand_obj = None
                    course_obj = None
                    # The sheet names a strand (SHS rows) or a course (the
                    # bundled rows). The column decides which one it is: the
                    # bundled sheets put the qualification in a "Course"
                    # column.
                    if track_strand:
                        strand_obj = _match_strand(track_strand)
                        if not strand_obj:
                            # A bundled sheet may carry the previous TESDA
                            # qualification title ("Food and Beverage
                            # Services NC II" before the 2024 rename).
                            course_obj = _match_course(track_strand)
                    if sheet_course and not course_obj:
                        course_obj = _match_course(sheet_course)
                        if not course_obj and not strand_obj:
                            strand_obj = _match_strand(sheet_course)
                    # "Industrial Technologies" is a DepEd *cluster*: one sheet
                    # value covers several of the school's strands, so it can
                    # only be matched by hand (as an alias). Counted as
                    # unmapped for now; the section may still supply the
                    # strand further down.

                    # ---- place the row in a section ----------------------------
                    # The school's sheets carry NO Section column - they name
                    # the strand. The sections are configured with their
                    # strand, so the row is placed into the section of that
                    # year level which teaches the strand (or the course for
                    # a bundled row). The emptiest section takes it.
                    if not section and not is_graduated_row:
                        # The sheet is the list of ONE class, and the file
                        # name says which ("G-11-THESSALONIANS-FBS.csv" is the
                        # Thessalonians class). The section the admin set up
                        # is the authority on what that class teaches, so a
                        # row whose strand fits one of them goes there - and
                        # a row whose wording names no strand at all (a
                        # cluster, or a bundled qualification) belongs to the
                        # class of the file.
                        if file_section_objs:
                            chosen = None
                            if strand_obj:
                                chosen = next(
                                    (
                                        s
                                        for s in file_section_objs
                                        if s.strand_id == strand_obj.id
                                    ),
                                    None,
                                )
                            if chosen is None and course_obj:
                                chosen = next(
                                    (
                                        s
                                        for s in file_section_objs
                                        if s.course_id == course_obj.id
                                    ),
                                    None,
                                )
                            if (
                                chosen is None
                                and not strand_obj
                                and not course_obj
                            ):
                                chosen = file_section_objs[0]
                            if chosen is not None:
                                section = chosen.name
                                rows_placed_by_file += 1
                        if not section and (strand_obj or course_obj):
                            if level_type == "SHS":
                                target_year = (
                                    "Grade 12" if shs_grade == "12" else "Grade 11"
                                )
                            elif level_type in ("BUN", "COL"):
                                target_year = (
                                    "2nd Year" if college_year == "2" else "1st Year"
                                )
                            else:
                                target_year = ""
                            placed = _pick_section(
                                level_type,
                                target_year,
                                strand_obj,
                                course_obj,
                                section_counts,
                            )
                            if placed:
                                section = placed
                                rows_placed_by_strand += 1
                                # Keep the count current, so the next row goes
                                # to the next emptiest section and the classes
                                # stay even.
                                section_counts[placed] = (
                                    section_counts.get(placed, 0) + 1
                                )
                                if len(rows_placed_by_strand_list) < 6:
                                    rows_placed_by_strand_list.append(
                                        f"Row {row_num} (LRN {lrn}) -> {placed}"
                                    )

                    # A row without a section lands in "Unassigned" on the
                    # Sections page, so it is counted and reported instead of
                    # disappearing silently.
                    if section:
                        rows_with_section += 1
                    elif len(rows_without_section) < 6:
                        rows_without_section.append(f"Row {row_num} (LRN {lrn})")

                    # ---- section record ---------------------------------------                    # The import owns its sections: a section that appears in the
                    # file but not in the system is created, so the class lists
                    # and the sections page line up with the enrollment sheet.
                    section_obj = None
                    if section and not is_graduated_row:
                        from tracks.models import Section as SectionModel

                        grade_year = ""
                        if level_type == "SHS":
                            grade_year = "Grade 12" if shs_grade == "12" else "Grade 11"
                        elif level_type == "BUN":
                            grade_year = "2nd Year" if college_year == "2" else "1st Year"

                        section_defaults = {
                            "level_type": level_type,
                            "grade_year": grade_year or None,
                        }
                        if strand_obj:
                            section_defaults["strand"] = strand_obj
                        if course_obj:
                            section_defaults["course"] = course_obj

                        section_obj, created_section = SectionModel.objects.get_or_create(
                            name=section, defaults=section_defaults
                        )
                        if created_section:
                            sections_created += 1
                        else:
                            # Keep the section's links in step with the file, but
                            # never overrule a strand the admin already set on
                            # their own section: the section is the authority on
                            # which strand a class belongs to.
                            changed_fields = []
                            for field, value in section_defaults.items():
                                if field in ("strand", "course"):
                                    if getattr(section_obj, f"{field}_id", None):
                                        continue
                                if value and getattr(section_obj, field, None) != value:
                                    setattr(section_obj, field, value)
                                    changed_fields.append(field)
                            if changed_fields:
                                section_obj.save(update_fields=changed_fields)
                                sections_updated += 1

                    # The section is the authority on what its class teaches:
                    # a sheet whose wording names no strand (a cluster like
                    # "Industrial Technologies", or a bundled qualification)
                    # inherits the strand and the course of the class the
                    # student is enrolled in.
                    if section_obj is not None:
                        if (
                            not strand_obj
                            and not course_obj
                            and getattr(section_obj, "strand_id", None)
                        ):
                            strand_obj = section_obj.strand
                            strands_inherited += 1
                        if (
                            not course_obj
                            and getattr(section_obj, "course_id", None)
                            and section_obj.level_type in ("BUN", "COL")
                        ):
                            course_obj = section_obj.course
                    if not strand_obj and not course_obj and (track_strand or sheet_course):
                        unmapped = track_strand or sheet_course
                        unmapped_strands[unmapped] = (
                            unmapped_strands.get(unmapped, 0) + 1
                        )
                    # A bundled class is a programme (course), an SHS class
                    # is a strand. When a title matches both - the
                    # qualification names are shared - the level decides
                    # which one the student gets.
                    if level_type in ("BUN", "COL") and course_obj is not None:
                        strand_obj = None
                    elif level_type == "SHS" and strand_obj is not None:
                        course_obj = None

                    # ---- create or update the student -------------------------
                    # Update in place with only what the sheet actually
                    # provides. The old behaviour overwrote every field on
                    # re-import, which wiped tuition balances and statuses.
                    provided = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "middle_name": middle_name,
                        "level_type": level_type,
                        "enrollment_status": enrollment_status,
                        "shs_grade": shs_grade,
                        "college_year": college_year,
                        # The strand the school records (or the bundled
                        # course); the sheet's own wording is only used when
                        # the sheet names something the app does not know.
                        "track_strand": (
                            strand_obj.name
                            if strand_obj
                            else (
                                course_obj.name
                                if course_obj
                                else (track_strand or sheet_course or None)
                            )
                        ),
                        "section": section or None,
                        "current_grade_level": canonical_grade or None,
                        "address": address or None,
                        "gender": gender or None,
                        "date_of_birth": _parse_dob(dob) if dob else None,
                        "contact_number": contact_number or None,
                        "guardian_name": guardian_name or None,
                        "guardian_contact": guardian_contact or None,
                        "guardian_address": guardian_address or None,
                    }
                    if is_graduated_row:
                        provided["status"] = "Graduated"
                        provided["graduated_sy"] = _current_school_year() or None
                    if strand_obj:
                        provided["strand"] = strand_obj
                    if course_obj:
                        provided["course_fk"] = course_obj
                        # The plain course name too: the app's forms show it.
                        provided["course"] = course_obj.name
                    if row_school_year:
                        provided["school_year"] = row_school_year

                    # The person this row is about. The school lists some
                    # students twice in one sheet - the same name, the same
                    # date of birth, a corrected number on the second line.
                    person_key = (
                        (first_name or "").strip().lower(),
                        (middle_name or "").strip().lower(),
                        (last_name or "").strip().lower(),
                        _parse_dob(dob) if dob else None,
                    )
                    seen = seen_students.get(person_key)
                    if seen is not None:
                        # The same person on a second line: one student, and
                        # the later line counts.
                        if lrn and seen.lrn != lrn:
                            clash = (
                                Student.objects.filter(lrn=lrn)
                                .exclude(pk=seen.pk)
                                .first()
                            )
                            if clash:
                                # The number of the later line already
                                # belongs to another record - that record is
                                # the duplicate and goes.
                                clash.delete()
                                merged_duplicates += 1
                            seen.lrn = lrn
                            upgraded_lrn = True
                        student = seen
                    else:
                        student = Student.objects.filter(lrn=lrn).first()
                        if student is None:
                            # The sheet may carry the number with a stray
                            # quote ("117414100000'") while the roster still
                            # holds the old form - the same student, one
                            # character apart.
                            for variant in (lrn + "'", "'" + lrn):
                                student = Student.objects.filter(lrn=variant).first()
                                if student:
                                    student.lrn = lrn
                                    upgraded_lrn = True
                                    break
                    if student is None and first_name and last_name and dob:
                        # The same person may already be in the roster under
                        # another number: the school's sheets list some
                        # students twice, once with the real LRN and once
                        # with the number Excel rounded away. The name and
                        # the date of birth tell them apart.
                        same_person = Student.objects.filter(
                            last_name__iexact=last_name,
                            first_name__iexact=first_name,
                            date_of_birth=_parse_dob(dob),
                        ).order_by("id")
                        if middle_name:
                            same_person = same_person.filter(
                                middle_name__iexact=middle_name
                            )
                        if used_placeholder:
                            # This row has no usable LRN - keep the student
                            # that is already on the roster.
                            student = same_person.first()
                        else:
                            # The row carries a real LRN, but no student has
                            # it yet: the placeholder of an earlier import
                            # is upgraded instead of a second student being
                            # created for the same person.
                            placeholder_student = same_person.filter(
                                lrn__startswith="0"
                            ).first()
                            if placeholder_student:
                                student = placeholder_student
                                student.lrn = lrn
                                upgraded_lrn = True
                                placeholder_upgraded += 1
                            else:
                                # The roster has this person under another
                                # number - the school corrected it, so the
                                # sheet wins.
                                known = same_person.first()
                                if known:
                                    student = known
                                    student.lrn = lrn
                                    upgraded_lrn = True
                                    merged_duplicates += 1
                    if student:
                        changed = []
                        if upgraded_lrn:
                            changed.append("lrn")
                        for field, value in provided.items():
                            if value in (None, ""):
                                # A graduate must shed the year level they
                                # finished; other empty cells are left alone.
                                if not (
                                    is_graduated_row
                                    and field in ("shs_grade", "college_year")
                                ):
                                    continue
                            if getattr(student, field, None) != value:
                                setattr(student, field, value)
                                changed.append(field)
                        if changed:
                            student.save(update_fields=changed)
                        updated_count += 1
                    else:
                        student = Student.objects.create(
                            lrn=lrn,
                            **{
                                k: v for k, v in provided.items() if v not in (None, "")
                            },
                        )
                        created_count += 1
                    seen_students[person_key] = student

                    # ---- tuition ledger ---------------------------------------
                    # A student imported with a fee gets their fee set and, if
                    # the sheet also carries an Amount Paid, a payment row in
                    # that school year's ledger. Other years' rows are never
                    # touched, and re-importing does not stack a second row
                    # for the same year.
                    if tuition_fee is not None and not is_graduated_row:
                        from tuition.models import TuitionPayment as _TuitionPayment

                        if tuition_paid_amount > tuition_fee:
                            warnings.append(
                                f"Row {row_num}: amount paid ({tuition_paid_amount}) is more than "
                                f"the tuition fee ({tuition_fee}) - the excess was not recorded."
                            )
                            tuition_paid_amount = tuition_fee

                        # The balance is the fee minus what is already paid:
                        # the sheet's Amount Paid is that year's TOTAL, so it
                        # replaces the row rather than adding to it, and only
                        # the other years' payments are added on top.
                        year_rows = _TuitionPayment.objects.filter(
                            student=student, school_year=row_school_year
                        )
                        year_paid = year_rows.aggregate(_s=Sum("amount"))["_s"] or Decimal("0")
                        other_years_paid = (
                            _TuitionPayment.objects.filter(student=student)
                            .exclude(school_year=row_school_year)
                            .aggregate(_s=Sum("amount"))["_s"]
                            or Decimal("0")
                        )
                        effective_year_paid = (
                            tuition_paid_amount if tuition_paid_amount > 0 else year_paid
                        )

                        student.custom_tuition_fee = tuition_fee
                        student.tuition_balance = max(
                            Decimal("0"),
                            tuition_fee - other_years_paid - effective_year_paid,
                        )
                        student.save(
                            update_fields=["custom_tuition_fee", "tuition_balance"]
                        )

                        if tuition_paid_amount > 0:
                            existing = (
                                _TuitionPayment.objects.filter(
                                    student=student, school_year=row_school_year
                                )
                                .order_by("-id")
                                .first()
                            )
                            if existing:
                                # The sheet states the year's total paid, so
                                # it REPLACES the row's amount - adding it
                                # again would double-count on every re-import.
                                existing.amount = tuition_paid_amount
                                existing.notes = "Enrollment import (updated)"
                                existing.save(update_fields=["amount", "notes"])
                            else:
                                _TuitionPayment.objects.create(
                                    student=student,
                                    school_year=row_school_year,
                                    amount=tuition_paid_amount,
                                    method=tuition_method,
                                    payment_method=tuition_method,
                                    payment_date=timezone.localdate(),
                                    notes="Enrollment import",
                                    remarks="Initial payment from enrollment import",
                                )

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                finally:
                    # One row is done (processed, skipped or failed) - the
                    # loading screen polls this while the request runs.
                    if progress_id:
                        entry = _BULK_IMPORT_PROGRESS.get(progress_id)
                        if entry is not None:
                            entry["done"] = min(entry["total"], entry["done"] + 1)

            if progress_id and progress_id in _BULK_IMPORT_PROGRESS:
                _BULK_IMPORT_PROGRESS[progress_id]["finished"] = True
                _BULK_IMPORT_PROGRESS[progress_id]["summary"] = {
                    "created": created_count,
                    "updated": updated_count,
                    "skipped": skipped_count,
                    "errors": len(errors),
                }

            return Response(
                {
                    "success": True,
                    "message": f"Successfully processed {created_count + updated_count} students",
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "skipped_count": skipped_count,
                    "total_rows_processed": row_num - 1,
                    # Sections are created from the file, so the class lists
                    # match the enrollment sheet without manual setup.
                    "sections_created": sections_created,
                    "sections_updated": sections_updated,
                    # What the importer understood, so a file whose columns
                    # are named differently can be diagnosed at a glance.
                    "headers_found": headers,
                    "detected_columns": hmap,
                    "rows_with_section": rows_with_section,
                    # Rows that had no Section column and were placed into a
                    # section from the strand their sheet names.
                    "rows_placed_by_strand": rows_placed_by_strand,
                    "rows_placed_by_strand_sample": rows_placed_by_strand_list,
                    # Rows that were placed into the class their FILE NAME
                    # names ("ATS 1A", "HRS 1B", "Thessalonians").
                    "rows_placed_by_file": rows_placed_by_file,
                    # The classes the file name named.
                    "sections_named_in_file": file_sections,
                    # Rows that had no usable LRN and got a placeholder.
                    "rows_with_placeholder_lrn": placeholder_lrns,
                    # Placeholders that were replaced by the real LRN.
                    "placeholders_upgraded": placeholder_upgraded,
                    # Rows that named a student the sheet had already listed.
                    "rows_merged_duplicates": merged_duplicates,
                    "rows_without_section": rows_without_section,
                    # Strand/course names in the sheet that do not match any
                    # strand the school has. Add them as aliases on the right
                    # strand (or create the strand) and upload again.
                    "unmapped_strands": unmapped_strands,
                    # Students whose strand came from their section because the
                    # sheet used a cluster name ("Industrial Technologies").
                    "strands_inherited_from_section": strands_inherited,
                    "warnings": warnings[:20] if warnings else [],
                    "errors": errors[:20] if errors else [],  # Limit errors to first 20
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="bulk_upload/progress")
    def import_progress(self, request):
        """Live progress of a running bulk import.

        The importing POST registers itself under a progress id the client
        generated and updates it per row; this endpoint is polled while that
        request is still running so the loading screen can count the students.
        """
        progress_id = str(request.query_params.get("id") or "").strip()
        entry = _BULK_IMPORT_PROGRESS.get(progress_id)
        if entry is None:
            return Response({"total": 0, "done": 0, "finished": False})
        return Response(
            {
                "total": entry.get("total", 0),
                "done": entry.get("done", 0),
                "finished": entry.get("finished", False),
                "summary": entry.get("summary"),
            }
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
        """Test endpoint to debug Excel uploads Ã¢â‚¬â€ DEBUG only."""
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


class StudentDocumentViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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


class DormPaymentViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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


class ProductViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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


class SaleViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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
        # Attribute the sale to the register (Electron X-Device-Id) and the
        # logged-in staff account. Done post-save because the create
        # serializer builds the row itself and does not accept extra fields;
        # a missing device header just leaves terminal NULL ("Unassigned").
        sale.terminal = resolve_terminal(request)
        sale.created_by = request.user if request.user.is_authenticated else None
        # Receipt numbers are minted in the browser from a per-device counter,
        # so two registers can mint the same OR number on the same day - and a
        # duplicate makes an official receipt ambiguous. When the number is
        # missing or already taken, the server assigns one that cannot
        # collide: it is built from this sale's own id.
        if (
            not sale.receipt_number
            or Sale.objects.filter(receipt_number=sale.receipt_number)
            .exclude(id=sale.id)
            .exists()
        ):
            sale.receipt_number = (
                f"OR-{timezone.localdate().strftime('%Y%m%d')}-{sale.id:05d}"
            )
        sale.save(update_fields=["terminal", "created_by", "receipt_number"])
        # Return using SaleSerializer for proper response
        response_serializer = SaleSerializer(sale)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        """Deleting a sale gives the stock back - the create path took a
        unit per line, so the delete path returns them."""
        from products.models import ProductVariant

        for item in instance.items.all():
            if item.variant_id is not None:
                variant = ProductVariant.objects.filter(id=item.variant_id).first()
                if variant is not None and variant.stock is not None:
                    variant.stock = variant.stock + int(item.quantity or 0)
                    variant.save(update_fields=["stock"])
            elif item.product is not None and not item.product.is_sized and item.product.stock is not None:
                item.product.stock = item.product.stock + int(item.quantity or 0)
                item.product.save(update_fields=["stock"])
        instance.delete()

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


class TuitionPaymentViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
    """Tuition payment management - handles payments and updates student balance"""

    serializer_class = TuitionPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TuitionPayment.objects.all().select_related("student").order_by("-date")

    def _ensure_unique_reference(self, payment):
        """The RCT reference is minted as max+1; two cashiers settling at the
        same moment can read the same max, so a collision is rewritten using
        the payment's own id - unique by construction."""
        if (
            payment.reference_number
            and TuitionPayment.objects.filter(
                reference_number=payment.reference_number
            )
            .exclude(id=payment.id)
            .exists()
        ):
            payment.reference_number = (
                f"RCT-{timezone.localdate().strftime('%Y%m%d')}-{payment.id}"
            )
            payment.save(update_fields=["reference_number"])

    def perform_destroy(self, instance):
        """Deleting a payment must bring the student's balance back in step
        with the rows that remain - the create path writes the balance, the
        delete path used to leave it stale."""
        from django.db import transaction
        from django.db.models import Sum as _Sum

        student = instance.student
        amount = instance.amount or Decimal("0")
        with transaction.atomic():
            instance.delete()
            remaining = (
                TuitionPayment.objects.filter(student=student)
                .aggregate(_s=_Sum("amount"))["_s"]
                or Decimal("0")
            )
            if student.custom_tuition_fee:
                student.tuition_balance = max(
                    Decimal("0"), student.custom_tuition_fee - remaining
                )
            else:
                # No fee on record - the balance was simply reduced by the
                # payment, so give the taken amount back.
                student.tuition_balance = max(
                    Decimal("0"), (student.tuition_balance or Decimal("0")) + amount
                )
            student.save(update_fields=["tuition_balance"])

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
                # Initial tuition setup mode Ã¢â‚¬â€ set student's balance to total_tuition minus amount_paid
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
                    # The RCT reference is minted as max+1; two cashiers
                    # settling at the same moment can read the same max and
                    # the unique constraint rejects the second insert. Retry
                    # with a reference built from a random token instead of
                    # failing the payment on the school's busiest day.
                    payment_kwargs = dict(
                        student=student,
                        amount=this_payment,
                        method=method,
                        reference_number=ref_number,
                        payment_date=parsed_payment_date,
                        payment_method=payment_method,
                        notes=notes or None,
                        remarks=description or "Initial payment upon enrollment",
                        terminal=resolve_terminal(request),
                        created_by=request.user if request.user.is_authenticated else None,
                    )
                    for attempt in range(3):
                        try:
                            payment = TuitionPayment.objects.create(**payment_kwargs)
                            self._ensure_unique_reference(payment)
                            break
                        except IntegrityError:
                            if attempt == 2:
                                raise
                            payment_kwargs["reference_number"] = (
                                f"RCT-{timezone.localdate().strftime('%Y%m%d')}-"
                                + uuid4().hex[:8].upper()
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

            payment_kwargs = dict(
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
                terminal=resolve_terminal(request),
                created_by=request.user if request.user.is_authenticated else None,
            )
            for attempt in range(3):
                try:
                    payment = TuitionPayment.objects.create(**payment_kwargs)
                    self._ensure_unique_reference(payment)
                    break
                except IntegrityError:
                    if attempt == 2:
                        raise
                    payment_kwargs["reference_number"] = (
                        f"RCT-{timezone.localdate().strftime('%Y%m%d')}-"
                        + uuid4().hex[:8].upper()
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
        """Update a tuition record and keep the student's ledger consistent.

        The Students page edits a student's tuition as a pair: the fee for the
        school year and the running total PAID for that year. Writing that
        running total into the edited row inflated the year's total - a
        student with two payments of 3,000 showed 12,000 paid when 9,000 was
        entered - and the payment method was stored lower-cased.

        The edited row therefore carries only the part of the year's total
        that the other rows of that year do not already cover.
        """
        from decimal import Decimal
        from django.db import transaction

        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        total_tuition = request.data.get("total_tuition")
        amount_paid = request.data.get("amount_paid")
        student_id = request.data.get("student_id") or instance.student_id
        school_year = request.data.get("school_year") or instance.school_year or ""

        if total_tuition is None and amount_paid is None:
            # A plain edit of the row's own fields. Partial, so a caller can
            # send just { amount } or { notes } without the full payload.
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)

        try:
            total_d = Decimal(str(total_tuition)) if total_tuition is not None else None
            paid_d = Decimal(str(amount_paid)) if amount_paid is not None else None
        except (TypeError, ValueError, ArithmeticError):
            return Response(
                {"error": "Invalid total_tuition or amount_paid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            student = (
                Student.objects.select_for_update().filter(id=student_id).first()
            )
            if student is None:
                return Response(
                    {"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # The payments of that school year other than the edited one.
            others = TuitionPayment.objects.filter(
                student=student, school_year=school_year
            ).exclude(pk=instance.pk)
            other_paid = others.aggregate(_s=Sum("amount"))["_s"] or Decimal("0")

            if paid_d is not None:
                if paid_d < other_paid:
                    return Response(
                        {
                            "error": (
                                f"The other payments for {school_year or 'this school year'} "
                                f"already total {other_paid}."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                row_amount = paid_d - other_paid
            else:
                row_amount = Decimal(str(instance.amount))

            if row_amount == 0 and not others.exists():
                # Nothing is paid for that year any more - drop the row
                # instead of leaving a zero payment in the ledger.
                instance.delete()
            else:
                instance.amount = row_amount
                instance.school_year = school_year or instance.school_year
                method = request.data.get("payment_method")
                if method:
                    method_map = {
                        "cash": "Cash",
                        "gcash": "GCash",
                        "check": "Bank Transfer",
                        "bank_transfer": "Bank Transfer",
                        "card": "Credit/Debit Card",
                    }
                    instance.method = method_map.get(str(method).lower(), "Cash")
                payment_date = request.data.get("payment_date")
                if payment_date:
                    try:
                        instance.payment_date = datetime.strptime(
                            payment_date, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass
                if request.data.get("notes") is not None:
                    instance.notes = request.data.get("notes") or None
                instance.save()

            # The student's fee and balance for that school year. The balance
            # always follows what the year really holds: the other rows plus
            # the edited one.
            year_paid = other_paid + row_amount
            fee_d = (
                total_d
                if total_d is not None
                else (student.custom_tuition_fee or Decimal("0"))
            )
            if total_d is not None:
                student.custom_tuition_fee = total_d
            student.tuition_balance = max(Decimal("0"), fee_d - year_paid)
            if school_year:
                student.school_year = school_year
            student.save(
                update_fields=["custom_tuition_fee", "tuition_balance", "school_year"]
            )

        return Response(
            {
                "success": True,
                "student_id": student.id,
                "student_name": f"{student.first_name} {student.last_name}",
                "total_tuition": float(student.custom_tuition_fee or 0),
                "amount_paid": float(paid_d if paid_d is not None else 0),
                "remaining_balance": float(student.tuition_balance or 0),
                "school_year": school_year,
            }
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
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


class GraduationPaymentViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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
                    "error": f"Amount cannot exceed balance of Ã¢â€šÂ±{student_graduation.balance}"
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
                created_by=request.user,
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


class AssessmentPaymentViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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
                        "error": f"Payment amount (Ã¢â€šÂ±{amount:.2f}) exceeds remaining balance (Ã¢â€šÂ±{assessment.balance:.2f})"
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
            created_by=request.user,
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


class TourPaymentViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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
                        "error": f"Payment amount (Ã¢â€šÂ±{amount:.2f}) exceeds remaining balance (Ã¢â€šÂ±{enrollment.balance:.2f})"
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
            created_by=request.user,
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
            .select_related("student", "terminal", "created_by")
            .prefetch_related("items__product")
        )

        # Get tuition payments
        tuition_payments = TuitionPayment.objects.all().select_related(
            "student", "terminal", "created_by"
        )

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
                        # Register that took the sale; None = "Unassigned"
                        # (old rows and plain-browser sessions).
                        "terminal": (
                            sale.terminal.name or sale.terminal.device_id
                        ) if sale.terminal else None,
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
                        "terminal": (
                            payment.terminal.name or payment.terminal.device_id
                        ) if payment.terminal else None,
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

        # Revenue by terminal (POS + tuition Ã¢â‚¬â€ the two transaction kinds a
        # register actually takes). Grouped from the same filtered querysets
        # as the rows above, so date range, search and type filters apply
        # here too. Grand totals above are intentionally untouched.
        buckets = {}

        def _display_name(device_id, raw_name):
            return raw_name or (f"Device {device_id[-6:]}" if device_id else "Unassigned")

        def _staff_name(first, last, username=None):
            name = f"{first or ''} {last or ''}".strip()
            if not name:
                # Some staff accounts (e.g. admin logins) have no profile
                # name Ã¢â‚¬â€ fall back to the username so the Staff column is
                # never blank when a user is actually recorded.
                name = (username or "").strip()
            return name or None

        def _bucket(device_id, terminal_name, staff_name):
            key = device_id or "__unassigned__"
            b = buckets.setdefault(key, {
                "terminal_id": device_id,
                "terminal_name": terminal_name,
                "staff_names": [],
                "pos": Decimal("0"),
                "tuition": Decimal("0"),
                "transactions": 0,
            })
            if staff_name and staff_name not in b["staff_names"]:
                b["staff_names"].append(staff_name)
            return b

        if revenue_type in ("", "pos"):
            for r in (
                pos_sales.values(
                    "terminal__device_id",
                    "terminal__name",
                    "created_by__first_name",
                    "created_by__last_name",
                    "created_by__username",
                )
                .annotate(pos_sum=Sum("amount_paid"), txn=Count("id"))
            ):
                device_id = r["terminal__device_id"]
                b = _bucket(
                    device_id,
                    _display_name(device_id, r["terminal__name"]),
                    _staff_name(r["created_by__first_name"], r["created_by__last_name"], r["created_by__username"]),
                )
                b["pos"] += r["pos_sum"] or Decimal("0")
                b["transactions"] += r["txn"]

        if revenue_type in ("", "tuition"):
            for r in (
                tuition_payments.values(
                    "terminal__device_id",
                    "terminal__name",
                    "created_by__first_name",
                    "created_by__last_name",
                    "created_by__username",
                )
                .annotate(tuition_sum=Sum("amount"), txn=Count("id"))
            ):
                device_id = r["terminal__device_id"]
                b = _bucket(
                    device_id,
                    _display_name(device_id, r["terminal__name"]),
                    _staff_name(r["created_by__first_name"], r["created_by__last_name"], r["created_by__username"]),
                )
                b["tuition"] += r["tuition_sum"] or Decimal("0")
                b["transactions"] += r["txn"]

        # "Unassigned" sorts last; the rest alphabetical so Terminal 1..N
        # read in order.
        by_terminal = sorted(
            (
                {
                    "terminal_id": b["terminal_id"],
                    "terminal_name": b["terminal_name"],
                    "staff_names": sorted(b["staff_names"]),
                    "pos": float(b["pos"]),
                    "tuition": float(b["tuition"]),
                    "total": float(b["pos"] + b["tuition"]),
                    "transactions": b["transactions"],
                }
                for b in buckets.values()
            ),
            key=lambda r: (r["terminal_name"] == "Unassigned", r["terminal_name"].lower()),
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
                # Cross-terminal aggregation is admin-only data: a cashier
                # login must not learn the takings of other registers.
                "by_terminal": by_terminal if request.user.is_superuser else [],
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


class PaymentViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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


class StudentChargeViewSet(SuperUserDeleteMixin, viewsets.ModelViewSet):
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
            created_by=request.user,
            terminal=resolve_terminal(request),
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


class TerminalViewSet(viewsets.ReadOnlyModelViewSet):
    """POS terminals registered from Electron device ids.

    `current` resolves the calling device from its X-Device-Id header, so the
    cashier can label receipts with the terminal name the admin set in
    Django admin. Unnamed devices report their auto-assigned Device name;
    plain-browser sessions report null.
    """

    queryset = Terminal.objects.all()
    serializer_class = TerminalSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # The full terminal inventory (device ids, per-register takings) is
        # admin-only. `current` and `retrieve` stay open so cashier receipts
        # and the "My Terminal" card keep working.
        if self.action == "list":
            return [IsSuperUser()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def current(self, request):
        terminal = resolve_terminal(request)
        if terminal is None:
            return Response({"terminal": None})
        return Response(
            {
                "terminal": {
                    "id": terminal.id,
                    "device_id": terminal.device_id,
                    "name": terminal.name or None,
                }
            }
        )


class AdviserViewSet(viewsets.ModelViewSet):
    """Advisers managed from School Config; sections point at one.

    Every staff login may list (dropdowns need it); only superusers may add,
    rename or deactivate â€” the same split as the terminal inventory.
    """

    queryset = Adviser.objects.all()
    serializer_class = AdviserSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsSuperUser()]

    def get_queryset(self):
        qs = Adviser.objects.all()
        if self.request.query_params.get("all") not in ("true", "1"):
            qs = qs.filter(is_active=True)
        return qs


class DisbursementViewSet(viewsets.ModelViewSet):
    """Register expenses the cashier logs as they happen.

    Cashiers see and manage only their own entries; superusers see all.
    """

    serializer_class = DisbursementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Disbursement.objects.all()
        if not self.request.user.is_superuser:
            qs = qs.filter(created_by=self.request.user)
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(date=date)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


def _collect_daily_rows(user, start, end):
    """Group all money-in inside the clock window.

    Reads the same sources Revenue reads, so the daily report can never
    disagree with the register. A superuser's report covers the whole school
    day (every register); a staff report covers only their own recorded
    payments. `start` is exclusive, `end` inclusive: a payment recorded after
    a report was generated belongs to the next one. Dorm payments are skipped
    â€” no SPA flow creates them, so they carry no cashier attribution yet.
    """
    scope_all = bool(user and user.is_superuser)
    rows = {}

    def add(label, amount, source, count=1):
        if not amount:
            return
        row = rows.setdefault(
            label,
            {"description": label, "amount": 0.0, "count": 0, "source": source},
        )
        row["amount"] = round(row["amount"] + float(amount), 2)
        row["count"] = int(row.get("count") or 0) + int(count or 0)

    def sale_q(**kw):
        q = dict(kw)
        if not scope_all:
            q["sale__created_by"] = user
        return SaleItem.objects.filter(**q)

    items = sale_q(
        sale__created_at__gt=start,
        sale__created_at__lte=end,
    ).select_related("product")
    for item in items:
        name = (
            item.product.name
            if item.product
            else (item.custom_item_name or "").strip() or "Custom Item"
        )
        add(name, item.price * item.quantity, "POS", item.quantity or 1)

    def pay_q(qs, **kw):
        if not scope_all:
            kw["created_by"] = user
        return qs.filter(**kw)

    tuition_rows = pay_q(
        TuitionPayment.objects, created_at__gt=start, created_at__lte=end
    ).aggregate(s=Sum("amount"), c=Count("id"))
    add("Tuition Fees", tuition_rows["s"], "Tuition", tuition_rows["c"] or 0)

    for r in (
        pay_q(TourPayment.objects, created_at__gt=start, created_at__lte=end)
        .values("tour__name")
        .annotate(s=Sum("amount"), c=Count("id"))
    ):
        add(
            f"TOUR - {r['tour__name'] or 'Educational Tour'}", r["s"], "Tour", r["c"] or 0
        )

    for r in (
        pay_q(AssessmentPayment.objects, created_at__gt=start, created_at__lte=end)
        .values("assessment_type__name")
        .annotate(s=Sum("amount"), c=Count("id"))
    ):
        add(
            r["assessment_type__name"] or "Assessment",
            r["s"],
            "Assessment",
            r["c"] or 0,
        )

    for r in (
        pay_q(GraduationPayment.objects, created_at__gt=start, created_at__lte=end)
        .values("graduation_event__name")
        .annotate(s=Sum("amount"), c=Count("id"))
    ):
        add(
            f"Graduation - {r['graduation_event__name'] or 'Fee'}",
            r["s"],
            "Graduation",
            r["c"] or 0,
        )

    # Charge settlements and walk-in fees live on Payment rows, keyed by
    # payment_type (the charge's item name, e.g. "Type B - Bundled").
    for r in (
        pay_q(Payment.objects, created_at__gt=start, created_at__lte=end)
        .values("payment_type")
        .annotate(s=Sum("amount"), c=Count("id"))
    ):
        add(
            (r["payment_type"] or "").strip() or "Other Collections",
            r["s"],
            "Payment",
            r["c"] or 0,
        )

    return sorted(rows.values(), key=lambda r: r["description"].lower())


class CashReportViewSet(viewsets.ViewSet):
    """Daily Collection & Disbursement Report â€” one per cashier per date.

    The clock is the cutoff: `generated_at` is the exact moment Generate is
    pressed and the window runs from the cashier's previous report's close
    (or midnight of the report date for the first one) up to that second.
    """

    permission_classes = [IsAuthenticated]

    def _period_start(self, user, report_date):
        tz = timezone.get_current_timezone()
        previous = (
            DailyCashReport.objects.filter(
                prepared_by=user, date__lt=report_date
            )
            .order_by("-date", "-generated_at")
            .first()
        )
        if previous:
            return previous.generated_at
        return timezone.make_aware(
            datetime.combine(report_date, datetime.min.time()), tz
        )

    def _denominations_total(self, denoms):
        bills = sum(
            float(denoms.get(key) or 0) * float(key)
            for key in ("1000", "500", "200", "100", "50", "20")
            if str(key) in denoms
        )
        return round(bills + float(denoms.get("coins") or 0), 2)

    def list(self, request):
        """GET /api/cash-reports/?date=YYYY-MM-DD â€” preview + saved report."""
        date_str = request.query_params.get("date")
        try:
            report_date = (
                datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_str
                else timezone.localdate()
            )
        except ValueError:
            return Response({"error": "date must be YYYY-MM-DD"}, status=400)

        period_start = self._period_start(request.user, report_date)
        now = timezone.now()
        saved = DailyCashReport.objects.filter(
            prepared_by=request.user, date=report_date
        ).first()

        return Response(
            {
                "date": report_date.isoformat(),
                "period_start": period_start.isoformat(),
                "generated_at": now.isoformat(),
                "auto_collections": _collect_daily_rows(
                    request.user, period_start, now
                ),
                "disbursements": list(
                    Disbursement.objects.filter(date=report_date)
                    .filter(
                        **({} if request.user.is_superuser else {"created_by": request.user})
                    )
                    .values("id", "description", "amount")
                ),
                "saved": (
                    DailyCashReportSerializer(saved).data if saved else None
                ),
            }
        )

    def create(self, request):
        """POST /api/cash-reports/ â€” snapshot and save (overwrites same date)."""
        data = request.data or {}
        date_str = data.get("date")
        try:
            report_date = (
                datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_str
                else timezone.localdate()
            )
        except ValueError:
            return Response({"error": "date must be YYYY-MM-DD"}, status=400)

        manual_rows = data.get("manual_rows") or []
        if not isinstance(manual_rows, list):
            return Response({"error": "manual_rows must be a list"}, status=400)
        denoms = data.get("denominations") or {}
        if not isinstance(denoms, dict):
            return Response({"error": "denominations must be an object"}, status=400)

        period_start = self._period_start(request.user, report_date)
        generated_at = timezone.now()

        collections = _collect_daily_rows(
            request.user, period_start, generated_at
        )
        for row in manual_rows:
            label = (row.get("description") or "").strip()
            try:
                amount = round(float(row.get("amount") or 0), 2)
            except (TypeError, ValueError):
                return Response(
                    {"error": "manual row amount must be a number"}, status=400
                )
            if label and amount:
                collections.append(
                    {
                        "description": label,
                        "amount": amount,
                        "count": 1,
                        "source": "Manual",
                    }
                )

        disb = list(
            Disbursement.objects.filter(date=report_date)
            .filter(**({} if request.user.is_superuser else {"created_by": request.user}))
            .values("description", "amount")
        )
        disb_rows = [
            {
                "description": d["description"],
                "amount": float(d["amount"]),
                "count": 1,
            }
            for d in disb
        ]

        total_collection = round(sum(r["amount"] for r in collections), 2)
        total_disbursement = round(sum(r["amount"] for r in disb_rows), 2)
        net_amount = round(total_collection - total_disbursement, 2)
        counted_total = self._denominations_total(denoms)

        report, _created = DailyCashReport.objects.update_or_create(
            prepared_by=request.user,
            date=report_date,
            defaults={
                "period_start": period_start,
                "generated_at": generated_at,
                "collections": collections,
                "disbursements": disb_rows,
                "denominations": {k: denoms[k] for k in denoms},
                "total_collection": total_collection,
                "total_disbursement": total_disbursement,
                "net_amount": net_amount,
                "counted_total": counted_total,
                "difference": round(counted_total - net_amount, 2),
            },
        )
        return Response(DailyCashReportSerializer(report).data, status=201)
