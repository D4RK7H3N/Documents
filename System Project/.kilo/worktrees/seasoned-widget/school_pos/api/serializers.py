from rest_framework import serializers
from django.db.models import Sum, Q
from students.models import Student, StudentDocument, StudentData
from dorm.models import DormBuilding, DormRoom, DormAssignment, DormPayment
from sales.models import Sale, SaleItem
from products.models import Product, ProductVariant
from tuition.models import TuitionPayment
from assessment.models import AssessmentType, StudentAssessment, AssessmentPayment
from tours.models import EducationalTour, TourEnrollment, TourPayment
from graduation.models import GraduationEvent, StudentGraduation, GraduationPayment
from tracks.models import Track, Strand, Course, Section
from payments.models import Payment, StudentCharge
from decimal import Decimal, DecimalException


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    """Student enrollment status serialized field"""

    class Meta:
        model = Student
        fields = [
            "id",
            "lrn",
            "first_name",
            "middle_name",
            "last_name",
            "level_type",
            "section",
        ]


# Graduation Serializers
class GraduationEventSerializer(serializers.ModelSerializer):
    """Serializer for GraduationEvent model"""

    total_participants = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()
    total_expected_revenue = serializers.SerializerMethodField()
    is_registration_open = serializers.SerializerMethodField()

    class Meta:
        model = GraduationEvent
        fields = [
            "id", "name", "event_date", "venue", "time", "description",
            "registration_deadline", "max_participants", "status",
            "graduation_package_fee", "total_fee_per_student",
            "created_at", "updated_at",
            "total_participants", "total_paid", "total_balance",
            "total_expected_revenue", "is_registration_open",
        ]

    def get_total_participants(self, obj):
        """Get total number of participants"""
        return obj.get_total_participants()

    def get_total_paid(self, obj):
        """Get total amount paid"""
        return float(obj.get_total_paid())

    def get_total_balance(self, obj):
        """Get total outstanding balance"""
        return float(obj.get_total_balance())

    def get_total_expected_revenue(self, obj):
        """Get total expected revenue"""
        return float(obj.get_total_expected_revenue())

    def get_is_registration_open(self, obj):
        """Check if registration is open"""
        return obj.is_registration_open()


class StudentGraduationSerializer(serializers.ModelSerializer):
    """Serializer for StudentGraduation model"""

    student_name = serializers.SerializerMethodField()
    student_lrn = serializers.SerializerMethodField()
    payment_progress = serializers.SerializerMethodField()
    event_name = serializers.SerializerMethodField()
    event_date = serializers.SerializerMethodField()
    event_venue = serializers.SerializerMethodField()

    class Meta:
        model = StudentGraduation
        fields = [
            "id", "student", "graduation_event", "graduation_level",
            "total_fee", "amount_paid", "balance", "status",
            "enrolled_at", "created_at", "updated_at",
                        "student_name",
            "lrn", "payment_progress",
            "event_name", "event_date", "event_venue",
        ]

    def get_student_name(self, obj):
        """Get full student name"""
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_student_lrn(self, obj):
        """Get student LRN"""
        return obj.student.lrn

    def get_payment_progress(self, obj):
        """Get payment progress percentage"""
        return obj.get_payment_progress()

    def get_event_name(self, obj):
        """Get graduation event name"""
        return obj.graduation_event.name

    def get_event_date(self, obj):
        """Get graduation event date"""
        return obj.graduation_event.event_date

    def get_event_venue(self, obj):
        """Get graduation event venue"""
        return obj.graduation_event.venue


class GraduationPaymentSerializer(serializers.ModelSerializer):
    """Serializer for GraduationPayment model"""

    student_name = serializers.SerializerMethodField()
    event_name = serializers.SerializerMethodField()

    class Meta:
        model = GraduationPayment
        fields = [
            "id", "student", "graduation_event", "amount",
            "payment_method", "reference_number", "gcash_number",
            "remarks", "payment_date", "created_at",
            "student_name", "event_name",
        ]

    def get_student_name(self, obj):
        """Get full student name"""
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_event_name(self, obj):
        """Get graduation event name"""
        return obj.graduation_event.name


class StudentSerializer(serializers.ModelSerializer):
    # Computed fields for frontend compatibility
    tuition_fee = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    strand_display = serializers.SerializerMethodField()
    track_name = serializers.SerializerMethodField()
    strand_name = serializers.SerializerMethodField()
    breakdown = serializers.SerializerMethodField()
    billing_category_display = serializers.SerializerMethodField()
    last_payment_date = serializers.SerializerMethodField()
    student_id = serializers.CharField(source="lrn", read_only=True)
    phone = serializers.CharField(source="contact_number", read_only=True)
    # Was `CharField(read_only=True)`, which made DRF silently DISCARD any
    # address sent by EnrollPage / StudentsPage / EnrollmentForm on create and
    # update. It now maps to the real model field and is writable.
    address = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=2000
    )
    guardian_phone = serializers.CharField(source="guardian_contact", read_only=True)
    # Was missing from Meta.fields entirely, so guardian_contact was never
    # saved either (EnrollPage/StudentsPage both submit it).
    guardian_contact = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=20
    )
    # For setting strand by ID or auto-create by name
    strand_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )
    strand_input = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    # For setting section by auto-create
    section_input = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    # For setting course by auto-create (for COL/BUN)
    course_input = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    course_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )
    date_of_birth = serializers.DateField(
        required=False, allow_null=True
    )

    class Meta:
        model = Student
        fields = [
            "id",
            "lrn",
            "student_id",
            "first_name",
            "middle_name",
            "last_name",
            "gender",
            "date_of_birth",
            "email",
            "contact_number",
            "phone",
            "address",
            "level_type",
            "shs_grade",
            "college_year",
            "track_strand",
            "strand",
            "strand_id",
            "strand_input",
            "strand_display",
            "track_name",
            "strand_name",
            "section",
            "section_assigned_by",
            "section_assigned_at",
            "section_input",
            "course",
            "course_fk",
            "course_id",
            "course_input",
            "enrollment_status",
            "student_type",
            "status",
            "tuition_balance",
            "blood_type",
            "medical_conditions",
            "guardian_name",
            "guardian_contact",
            "guardian_phone",
            "emergency_contact",
            "tuition_fee",
            "balance",
            "total_paid",
            "grade",
            "custom_tuition_fee",
            "breakdown",
            # Cashier settlement panel context.
            "adviser",
            "billing_category",
            "billing_category_display",
            "last_payment_date",
        ]

    def get_billing_category_display(self, obj):
        return obj.get_billing_category_display()

    def get_last_payment_date(self, obj):
        """Most recent money movement for this student, or None.

        Derived rather than stored so it can never go stale.
        """
        from django.db.models import Max

        tuition = obj.tuition_payments.aggregate(m=Max("date"))["m"]
        payment = obj.payments.aggregate(m=Max("created_at"))["m"]
        candidates = [x for x in (tuition, payment) if x]
        return max(candidates) if candidates else None

    def get_track_name(self, obj):
        """Get the track name from the strand relationship"""
        if obj.strand and obj.strand.track:
            return obj.strand.track.name
        return None

    def get_strand_name(self, obj):
        """Get the strand name from the strand relationship"""
        if obj.strand:
            return obj.strand.name
        return obj.track_strand or None

    def get_strand_display(self, obj):
        """Get formatted strand display (Track - Strand)"""
        if obj.strand:
            return f"{obj.strand.track.name} - {obj.strand.name}"
        return obj.track_strand or ""

    def get_tuition_fee(self, obj):
        """Get the tuition fee for this student

        Calculated as: current balance + total payments made
        Or from custom_tuition_fee if set.
        """
        # First check for custom tuition fee
        if obj.custom_tuition_fee:
            return float(obj.custom_tuition_fee)

        # Calculate from balance + payments (backwards calculation)
        current_balance = float(obj.tuition_balance or 0)
        total_paid = self.get_total_paid(obj)
        calculated_fee = current_balance + total_paid

        return calculated_fee if calculated_fee > 0 else current_balance

    def get_balance(self, obj):
        """Get remaining tuition balance - use the stored value directly"""
        return float(obj.tuition_balance or 0)

    def get_total_paid(self, obj):
        """Get total tuition payments for this student"""
        try:
            total = TuitionPayment.objects.filter(student=obj).aggregate(
                total=Sum("amount")
            )["total"]
            return float(total) if total else 0.00
        except Exception:
            return 0.00

    def get_grade(self, obj):
        """Get the grade/year level display"""
        if obj.level_type == "SHS":
            return f"Grade {obj.shs_grade}" if obj.shs_grade else "Senior High"
        elif obj.level_type == "COL":
            year_map = {
                "1": "1st Year",
                "2": "2nd Year",
                "3": "3rd Year",
                "4": "4th Year",
            }
            return year_map.get(obj.college_year, "College")
        elif obj.level_type == "BUN":
            return f"Bundled Year {obj.college_year}" if obj.college_year else "Bundled"
        return obj.current_grade_level or "N/A"

    def get_breakdown(self, obj):
        """Get tuition breakdown based on level type.

        SHS: First Sem (first_quarter, second_quarter), Second Sem (third_quarter, fourth_quarter)
        BUN: First Sem, Second Sem only
        """
        tuition_fee = self.get_tuition_fee(obj)

        if obj.level_type == "SHS":
            half = tuition_fee / 2
            quarter = tuition_fee / 4
            return {
                "first_sem": half,
                "first_quarter": quarter,
                "second_quarter": quarter,
                "second_sem": half,
                "third_quarter": quarter,
                "fourth_quarter": quarter,
            }
        elif obj.level_type == "BUN":
            half = tuition_fee / 2
            return {
                "first_sem": half,
                "second_sem": half,
            }
        return None

    def _get_or_create_strand(self, strand_input, level_type="SHS"):
        """
        Get or create a strand from a string input.
        Supports formats:
        - "STEM" - Creates strand with auto-generated track
        - "Academic Track - STEM" - Creates track "Academic Track" and strand "STEM"
        """
        if not strand_input:
            return None

        strand_input = strand_input.strip()

        # First, try to find existing strand by name or code
        existing = Strand.objects.filter(
            Q(name__iexact=strand_input) | Q(code__iexact=strand_input)
        ).first()

        if existing:
            return existing

        # Check if it contains a separator (Track - Strand format)
        if " - " in strand_input:
            track_name, strand_name = strand_input.split(" - ", 1)
            track_name = track_name.strip()
            strand_name = strand_name.strip()
        else:
            # Single name - use as strand name, create general track
            track_name = "General Track"
            strand_name = strand_input

        # Generate codes
        track_code = "".join(word[0] for word in track_name.split()[:4]).upper()
        strand_code = "".join(word[0] for word in strand_name.split()[:4]).upper()

        # Ensure unique strand code
        if Strand.objects.filter(code=strand_code).exists():
            # Add number suffix to make unique
            count = Strand.objects.filter(code__startswith=strand_code).count()
            strand_code = f"{strand_code}{count + 1}"

        # Get or create track
        track, _ = Track.objects.get_or_create(
            code=track_code, defaults={"name": track_name, "level_type": level_type}
        )

        # Get or create strand
        strand, _ = Strand.objects.get_or_create(
            track=track, code=strand_code, defaults={"name": strand_name}
        )

        return strand

    def _get_or_create_section(self, section_input, level_type="SHS", grade_year=None):
        """
        Get or create a section from a string input.
        """
        if not section_input:
            return None

        section_input = section_input.strip()

        # First, try to find existing section
        existing = Section.objects.filter(Q(name__iexact=section_input)).first()

        if existing:
            return existing

        # Determine grade_year if not provided
        if not grade_year:
            if level_type == "SHS":
                grade_year = "Grade 11"
            elif level_type == "BUN":
                grade_year = "Year 1"
            elif level_type == "COL":
                grade_year = "1st Year"

        # Create new section
        section, _ = Section.objects.get_or_create(
            name=section_input, level_type=level_type, grade_year=grade_year
        )

        return section

    def _get_or_create_course(self, course_input, level_type="COL"):
        """
        Get or create a course from a string input (for COL/BUN students).
        """
        if not course_input:
            return None

        course_input = course_input.strip()

        # First, try to find existing course by name or code
        existing = Course.objects.filter(
            Q(name__iexact=course_input) | Q(code__iexact=course_input.upper())
        ).first()

        if existing:
            return existing

        # Generate code from name
        code = "".join(word[0] for word in course_input.split()[:4]).upper()

        # Ensure unique code
        if Course.objects.filter(code=code).exists():
            count = Course.objects.filter(code__startswith=code).count()
            code = f"{code}{count + 1}"

        # Create new course
        course, _ = Course.objects.get_or_create(
            code=code,
            defaults={
                "name": course_input,
                "level_type": level_type,
                "abbreviation": course_input[:10]
                if len(course_input) > 10
                else course_input,
            },
        )

        return course

    def create(self, validated_data):
        """Handle strand, section, and course auto-creation during student creation"""
        strand_id = validated_data.pop("strand_id", None)
        strand_input = validated_data.pop("strand_input", None)
        section_input = validated_data.pop("section_input", None)
        course_input = validated_data.pop("course_input", None)
        course_id = validated_data.pop("course_id", None)
        level_type = validated_data.get("level_type", "SHS")

        # Handle track_strand from frontend (alternative to strand_input)
        track_strand = validated_data.pop("track_strand", None)
        if strand_input is None and track_strand:
            strand_input = track_strand

        # Determine strand to use
        if strand_id:
            validated_data["strand"] = Strand.objects.filter(id=strand_id).first()
        elif strand_input:
            validated_data["strand"] = self._get_or_create_strand(
                strand_input, level_type
            )
            validated_data["track_strand"] = strand_input

        # Handle section - use section_input or fallback to section field
        section = validated_data.pop("section", None)
        if section_input:
            validated_data["section"] = section_input
        elif section:
            validated_data["section"] = section

        # Determine grade/year for section creation
        grade_year = None
        if level_type == "SHS":
            grade_year = f"Grade {validated_data.get('shs_grade', '11')}"
        elif level_type in ["BUN", "COL"]:
            year_map = {
                "1": "1st Year",
                "2": "2nd Year",
                "3": "3rd Year",
                "4": "4th Year",
            }
            grade_year = year_map.get(
                validated_data.get("college_year", "1"), "1st Year"
            )

        # Handle course (for COL/BUN students)
        if course_id:
            validated_data["course_fk"] = Course.objects.filter(id=course_id).first()
        elif course_input:
            validated_data["course_fk"] = self._get_or_create_course(
                course_input, level_type
            )
            validated_data["course"] = course_input

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Handle strand, section, and course auto-creation during student update"""
        strand_id = validated_data.pop("strand_id", None)
        strand_input = validated_data.pop("strand_input", None)
        section_input = validated_data.pop("section_input", None)
        course_input = validated_data.pop("course_input", None)
        course_id = validated_data.pop("course_id", None)
        level_type = validated_data.get("level_type", instance.level_type)

        # Handle track_strand from frontend (alternative to strand_input)
        track_strand = validated_data.pop("track_strand", None)
        if strand_input is None and track_strand:
            strand_input = track_strand

        # Determine strand to use
        if strand_id:
            validated_data["strand"] = Strand.objects.filter(id=strand_id).first()
        elif strand_input:
            validated_data["strand"] = self._get_or_create_strand(
                strand_input, level_type
            )
            validated_data["track_strand"] = strand_input

        # Handle section - use section_input or fallback to section field
        section = validated_data.pop("section", None)
        if section_input:
            validated_data["section"] = section_input
        elif section:
            validated_data["section"] = section

        # Determine grade/year for section creation
        grade_year = None
        if level_type == "SHS":
            grade_year = (
                f"Grade {validated_data.get('shs_grade', instance.shs_grade or '11')}"
            )
        elif level_type in ["BUN", "COL"]:
            year_map = {
                "1": "1st Year",
                "2": "2nd Year",
                "3": "3rd Year",
                "4": "4th Year",
            }
            college_year = validated_data.get(
                "college_year", instance.college_year or "1"
            )
            grade_year = year_map.get(college_year, "1st Year")

        # Handle course (for COL/BUN students)
        if course_id:
            validated_data["course_fk"] = Course.objects.filter(id=course_id).first()
        elif course_input:
            validated_data["course_fk"] = self._get_or_create_course(
                course_input, level_type
            )
            validated_data["course"] = course_input

        return super().update(instance, validated_data)


class StudentDetailSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source="lrn", read_only=True)
    phone = serializers.CharField(source="contact_number", read_only=True)
    guardian_phone = serializers.CharField(source="guardian_contact", read_only=True)
    enrollment_date = serializers.DateField(source="date_of_enrollment", read_only=True)
    billing_category_display = serializers.SerializerMethodField()
    last_payment_date = serializers.SerializerMethodField()

    def get_billing_category_display(self, obj):
        return obj.get_billing_category_display()

    def get_last_payment_date(self, obj):
        from django.db.models import Max

        tuition = obj.tuition_payments.aggregate(m=Max("date"))["m"]
        payment = obj.payments.aggregate(m=Max("created_at"))["m"]
        candidates = [x for x in (tuition, payment) if x]
        return max(candidates) if candidates else None

    # These fields are on the related StudentData model
    form_137_submitted = serializers.SerializerMethodField()
    psa_submitted = serializers.SerializerMethodField()
    good_moral_submitted = serializers.SerializerMethodField()
    report_card_submitted = serializers.SerializerMethodField()
    photos_submitted = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "lrn", "student_id", "first_name", "middle_name", "last_name",
            "gender", "date_of_birth", "email", "contact_number", "phone",
            "address", "photo", "nationality", "blood_type",
            "level_type", "shs_grade", "college_year",
            "current_grade_level", "enrollment_status", "student_type", "status",
            # Cashier settlement panel context.
            "adviser", "billing_category", "billing_category_display",
            "last_payment_date",
            "track_strand", "strand", "section",
            "course", "course_fk",
            "guardian_name", "guardian_phone", "guardian_contact",
            "guardian_address", "guardian_occupation", "guardian_relationship",
            "emergency_contact",
            "medical_conditions", "health_insurance",
            "preferred_hospital", "immunization_records",
            "form_137_submitted", "psa_submitted", "good_moral_submitted",
            "report_card_submitted", "photos_submitted",
            "previous_school", "is_als_graduate", "last_grade_completed",
            "scholarship_discount", "custom_tuition_fee", "tuition_balance",
            "academic_records", "extracurricular",
            "date_of_enrollment", "enrollment_date",
        ]

    def get_form_137_submitted(self, obj):
        try:
            return obj.enrollment_data.form_137_submitted
        except StudentData.DoesNotExist:
            return False

    def get_psa_submitted(self, obj):
        try:
            return obj.enrollment_data.psa_submitted
        except StudentData.DoesNotExist:
            return False

    def get_good_moral_submitted(self, obj):
        try:
            return obj.enrollment_data.good_moral_submitted
        except StudentData.DoesNotExist:
            return False

    def get_report_card_submitted(self, obj):
        try:
            return obj.enrollment_data.report_card_submitted
        except StudentData.DoesNotExist:
            return False

    def get_photos_submitted(self, obj):
        try:
            return obj.enrollment_data.photos_submitted
        except StudentData.DoesNotExist:
            return False


class StudentDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = StudentDocument
        fields = [
            "id",
            "student",
            "document_type",
            "file",
            "file_url",
            "description",
            "uploaded_at",
            "is_verified",
        ]
        # Without these, any authenticated user could PATCH is_verified or
        # swap the file on another student's document record.
        read_only_fields = ["id", "file", "file_url", "uploaded_at", "is_verified"]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class StudentDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentData
        fields = [
            "id",
            "student",
            "emergency_contact_name",
            "emergency_contact_number",
            "emergency_contact_relationship",
            "blood_type_choice",
            "health_concerns",
            "is_complete",
            "notes",
        ]


class DormBuildingSerializer(serializers.ModelSerializer):
    available_rooms_count = serializers.SerializerMethodField()

    class Meta:
        model = DormBuilding
        fields = [
            "id",
            "name",
            "gender_restriction",
            "total_rooms",
            "description",
            "available_rooms_count",
        ]

    def get_available_rooms_count(self, obj):
        available = DormRoom.objects.filter(building=obj, is_active=True).count()
        return available


class DormRoomSerializer(serializers.ModelSerializer):
    current_occupancy = serializers.SerializerMethodField()
    building_name = serializers.CharField(source="building.name", read_only=True)

    class Meta:
        model = DormRoom
        fields = [
            "id",
            "building",
            "building_name",
            "room_number",
            "capacity",
            "room_type",
            "monthly_rate",
            "is_available",
            "current_occupancy",
        ]

    def get_current_occupancy(self, obj):
        occupants = DormAssignment.objects.filter(room=obj, status="Active").count()
        return f"{occupants}/{obj.capacity}"


class DormAssignmentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    building_name = serializers.CharField(source="room.building.name", read_only=True)

    class Meta:
        model = DormAssignment
        fields = [
            "id",
            "student",
            "student_name",
            "room",
            "room_number",
            "building_name",
            "date_started",
            "date_ended",
            "status",
            "notes",
        ]

    def get_student_name(self, obj):
        return f"{obj.student.last_name}, {obj.student.first_name}"


class DormPaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    assignment_id = serializers.IntegerField(source="assignment.id", read_only=True)
    room_number = serializers.CharField(
        source="assignment.room.room_number", read_only=True
    )
    building_name = serializers.CharField(
        source="assignment.room.building.name", read_only=True
    )

    class Meta:
        model = DormPayment
        fields = [
            "id",
            "assignment",
            "assignment_id",
            "student_name",
            "room_number",
            "building_name",
            "amount",
            "month_covered",
            "year_covered",
            "payment_method",
            "receipt_number",
            "payment_date",
        ]

    def get_student_name(self, obj):
        return (
            f"{obj.assignment.student.last_name}, {obj.assignment.student.first_name}"
        )


class ProductVariantSerializer(serializers.ModelSerializer):
    """One size of a sized product."""

    effective_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = ProductVariant
        fields = ["id", "product", "size", "price", "stock", "effective_price"]
        read_only_fields = ["product", "effective_price"]


class ProductSerializer(serializers.ModelSerializer):
    # Sizes so the cashier can render a size picker for sized items.
    variants = ProductVariantSerializer(many=True, read_only=True)
    total_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "price", "stock", "category",
            "is_sized", "variants", "total_stock",
        ]


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = SaleItem
        fields = [
            "id",
            "product",
            "product_name",
            "custom_item_name",
            "quantity",
            "price",
            "subtotal",
            "variant",
            "size",
            "label",
        ]
        read_only_fields = ["label"]

    def get_product_name(self, obj):
        if obj.product:
            return obj.product.name
        return (obj.custom_item_name or "").strip() or "Custom Item"


class SaleSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "student",
            "student_name",
            "customer_name",
            "receipt_number",
            "total",
            "amount_paid",
            "balance",
            "payment_status",
            "payment_method",
            "gcash_number",
            "gcash_reference",
            "created_at",
            "updated_at",
            "items",
        ]

    def get_items(self, obj):
        items = obj.items.all()
        return SaleItemSerializer(items, many=True).data

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.first_name} {obj.student.last_name}"
        return obj.customer_name or "Walk-in Customer"

    def get_balance(self, obj):
        return float(obj.balance)


class SaleCreateSerializer(serializers.Serializer):
    """Serializer for creating sales with items"""

    student_id = serializers.IntegerField(required=False, allow_null=True)
    # The cashier sends `student`; other callers send `student_id`. Accept
    # both so a real buyer is never silently downgraded to a walk-in.
    student = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    customer_name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    # The OR number the cashier minted for this transaction.
    receipt_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=50
    )
    items = serializers.ListField(child=serializers.DictField())
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField(required=False, default="cash")
    amount_paid = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )
    gcash_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    gcash_reference = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    is_partial_payment = serializers.BooleanField(required=False, default=False)

    def create(self, validated_data):
        from django.db import transaction
        from decimal import Decimal

        items_data = validated_data.pop("items", [])
        # `student` (cashier) takes precedence, then `student_id`.
        student_id = validated_data.pop("student", None) or validated_data.pop("student_id", None)
        receipt_number = validated_data.pop("receipt_number", None) or None
        # Guard against a bad id so a typo is a validation error rather than
        # a 500 from the FK.
        if student_id is not None and not Student.objects.filter(id=student_id).exists():
            raise serializers.ValidationError(f"Student {student_id} does not exist.")
        customer_name = validated_data.pop("customer_name", None)
        payment_method = validated_data.pop("payment_method", "cash")
        amount_paid = Decimal(str(validated_data.pop("amount_paid", 0) or 0))
        gcash_number = validated_data.pop("gcash_number", None)
        gcash_reference = validated_data.pop("gcash_reference", None)
        is_partial = validated_data.pop("is_partial_payment", False)

        total = Decimal(str(validated_data["total"]))

        # Determine payment status
        if amount_paid >= total:
            payment_status = "paid"
        elif amount_paid > 0:
            payment_status = "partial"
        else:
            payment_status = "unpaid"

        with transaction.atomic():
            # Create the sale with payment info
            sale = Sale.objects.create(
                student_id=student_id,
                customer_name=customer_name,
                receipt_number=receipt_number,
                total=total,
                amount_paid=amount_paid,
                payment_status=payment_status,
                payment_method=payment_method,
                gcash_number=gcash_number,
                gcash_reference=gcash_reference,
            )

            # Create sale items
            for item_data in items_data:
                # Accept both `product_id` and `product`; the cashier sends
                # `product`. Falling back silently to a custom item used to
                # record "Custom Item" and skip stock entirely.
                product_id = item_data.get("product_id") or item_data.get("product")
                variant_id = item_data.get("variant") or item_data.get("variant_id")
                is_custom = item_data.get("is_custom", False)

                if is_custom or not product_id:
                    # Create custom sale item
                    product_name = (item_data.get("name") or "").strip()
                    SaleItem.objects.create(
                        sale=sale,
                        product=None,
                        custom_item_name=product_name or "Custom Item",
                        quantity=item_data["quantity"],
                        price=item_data["price"],
                    )
                else:
                    # Create regular sale item with product
                    product = Product.objects.filter(id=product_id).first()
                    if product is None:
                        raise serializers.ValidationError(
                            f"Product {product_id} does not exist."
                        )
                    variant = None
                    if variant_id:
                        variant = ProductVariant.objects.filter(
                            id=variant_id, product=product
                        ).first()
                        if variant is None:
                            raise serializers.ValidationError(
                                f"Variant {variant_id} does not belong to "
                                f"product '{product.name}'."
                            )

                    qty = int(item_data["quantity"])

                    # Stock guard for sized products before we commit anything.
                    if variant is not None and variant.stock is not None:
                        if variant.stock < qty:
                            raise serializers.ValidationError(
                                f"Only {variant.stock} left of "
                                f"'{product.name}' size {variant.size}."
                            )
                    elif not product.is_sized and product.stock is not None:
                        if product.stock < qty:
                            raise serializers.ValidationError(
                                f"Only {product.stock} left of '{product.name}'."
                            )

                    # A sized product must be sold by its size, not off the
                    # parent stock pool.
                    size = (item_data.get("size") or (variant.size if variant else None))
                    if product.is_sized and not size:
                        raise serializers.ValidationError(
                            f"'{product.name}' is a sized item - a size is required."
                        )

                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        variant=variant,
                        size=size,
                        quantity=qty,
                        price=item_data["price"],
                    )

                    # Update stock if tracking is enabled
                    if variant is not None:
                        if variant.stock is not None:
                            variant.stock = max(0, variant.stock - qty)
                            variant.save(update_fields=["stock"])
                    elif not product.is_sized and product.stock is not None:
                        product.stock = max(0, product.stock - qty)
                        product.save(update_fields=["stock"])

        return sale


class SalePaymentSerializer(serializers.Serializer):
    """Serializer for adding payments to existing sales"""

    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField(required=False, default="cash")
    gcash_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    gcash_reference = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class TuitionPaymentSerializer(serializers.ModelSerializer):
    """Serializer for individual tuition payments"""

    student_name = serializers.SerializerMethodField()
    lrn = serializers.CharField(source="student.lrn", read_only=True)
    previous_balance = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(),
        source='student',
        write_only=True,
        required=True
    )
    amount_paid = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        source='amount',
        write_only=True,
        required=True
    )
    payment_method = serializers.CharField(
        source='method',
        write_only=True,
        required=True
    )

    class Meta:
        model = TuitionPayment
        fields = [
            "id",
            "student",
            "student_id",
            "student_name",
            "lrn",
            "school_year",
            "amount",
            "amount_paid",
            "method",
            "payment_method",
            "gcash_number",
            "reference_no",
            "reference_number",
            "payment_date",
            "payment_method",
            "notes",
            "remarks",
            "date",
            "created_at",
            "previous_balance",
            "remaining_balance",
        ]
        read_only_fields = ["date", "created_at", "reference_number", "student"]

    def get_fields(self):
        fields = super().get_fields()
        # Make amount and method not required for partial updates
        if self.instance is not None:  # Update operation
            if 'amount' in fields:
                fields['amount'].required = False
            if 'method' in fields:
                fields['method'].required = False
        return fields

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_previous_balance(self, obj):
        """Get the balance before this payment was made"""
        return float(obj.student.tuition_balance) + float(obj.amount)

    def get_remaining_balance(self, obj):
        """Get the current remaining balance"""
        return float(obj.student.tuition_balance)


class TuitionRecordSerializer(serializers.Serializer):
    """Aggregated tuition record per student for list view"""

    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    lrn = serializers.CharField()
    grade = serializers.CharField()
    section = serializers.CharField(default="")
    total_tuition = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    # Amount paid beyond total_tuition. 0 when the account is not in credit.
    overpayment = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    status = serializers.CharField()
    payment_count = serializers.IntegerField()
    latest_payment_date = serializers.DateField(allow_null=True)
    latest_payment_method = serializers.CharField(allow_null=True)
    school_year = serializers.CharField(default="")


# ============== ASSESSMENT SERIALIZERS ==============


class AssessmentTypeSerializer(serializers.ModelSerializer):
    """Serializer for assessment types"""

    class Meta:
        model = AssessmentType
        fields = [
            "id",
            "name",
            "code",
            "category",
            "description",
            "amount",
            "applicable_to",
            "applicable_tracks",
            "is_active",
            "is_required",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for student assessments"""

    student_name = serializers.SerializerMethodField()
    assessment_name = serializers.CharField(
        source="assessment_type.name", read_only=True
    )
    assessment_code = serializers.CharField(
        source="assessment_type.code", read_only=True
    )
    payment_progress = serializers.SerializerMethodField()

    class Meta:
        model = StudentAssessment
        fields = [
            "id",
            "student",
            "student_name",
            "assessment_type",
            "assessment_name",
            "assessment_code",
            "total_fee",
            "amount_paid",
            "balance",
            "status",
            "date_assessed",
            "due_date",
            "notes",
            "assessed_by",
            "payment_progress",
            "created_at",
            "updated_at",
        ]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_payment_progress(self, obj):
        return obj.get_payment_progress()


class AssessmentPaymentSerializer(serializers.ModelSerializer):
    """Serializer for assessment payments"""

    student_name = serializers.SerializerMethodField()
    assessment_name = serializers.CharField(
        source="assessment_type.name", read_only=True
    )
    assessment_code = serializers.CharField(
        source="assessment_type.code", read_only=True
    )

    class Meta:
        model = AssessmentPayment
        fields = [
            "id",
            "assessment",
            "student",
            "student_name",
            "assessment_type",
            "assessment_name",
            "assessment_code",
            "amount",
            "payment_date",
            "payment_method",
            "reference_number",
            "gcash_number",
            "received_by",
            "remarks",
            "created_at",
        ]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"


# ============== TOUR SERIALIZERS ==============


class EducationalTourSerializer(serializers.ModelSerializer):
    """Serializer for educational tours"""

    total_participants = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()
    slots_available = serializers.SerializerMethodField()

    class Meta:
        model = EducationalTour
        fields = [
            "id",
            "name",
            "destination",
            "tour_company",
            "description",
            "tour_date",
            "return_date",
            "total_cost",
            "transportation_fee",
            "accommodation_fee",
            "food_allowance",
            "entrance_fees",
            "other_fees",
            "status",
            "max_participants",
            "total_participants",
            "total_paid",
            "total_balance",
            "slots_available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_participants",
            "total_paid",
            "total_balance",
            "slots_available",
            "created_at",
            "updated_at",
        ]

    def get_total_participants(self, obj):
        return obj.get_total_participants()

    def get_total_paid(self, obj):
        return float(obj.get_total_paid())

    def get_total_balance(self, obj):
        return float(obj.get_total_balance())

    def get_slots_available(self, obj):
        return obj.has_slots_available()


class TourEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for tour enrollments"""

    student_name = serializers.SerializerMethodField()
    student_lrn = serializers.CharField(source="student.lrn", read_only=True)
    tour_name = serializers.CharField(source="tour.name", read_only=True)
    tour_destination = serializers.CharField(source="tour.destination", read_only=True)
    payment_progress = serializers.SerializerMethodField()

    class Meta:
        model = TourEnrollment
        fields = [
            "id",
            "tour",
            "tour_name",
            "tour_destination",
            "student",
            "student_name",
            "student_lrn",
            "enrollment_date",
            "status",
            "total_fee",
            "amount_paid",
            "balance",
            "parent_consent",
            "medical_clearance",
            "notes",
            "payment_progress",
            "created_at",
            "updated_at",
        ]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_payment_progress(self, obj):
        return obj.get_payment_progress()


class TourPaymentSerializer(serializers.ModelSerializer):
    """Serializer for tour payments"""

    student_name = serializers.SerializerMethodField()
    tour_name = serializers.CharField(source="tour.name", read_only=True)

    class Meta:
        model = TourPayment
        fields = [
            "id",
            "enrollment",
            "tour",
            "tour_name",
            "student",
            "student_name",
            "amount",
            "payment_date",
            "method",
            "reference_number",
            "received_by",
            "remarks",
            "created_at",
            "updated_at",
        ]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for general (non-tuition) payments"""

    student_name = serializers.SerializerMethodField(read_only=True)
    payer_display_name = serializers.SerializerMethodField(read_only=True)
    lrn = serializers.CharField(source="student.lrn", read_only=True, default="")
    student_first_name = serializers.CharField(source="student.first_name", read_only=True, default="")
    student_last_name = serializers.CharField(source="student.last_name", read_only=True, default="")

    item_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "sale",
            "student",
            "student_name",
            "lrn",
            "student_first_name",
            "student_last_name",
            "payer_display_name",
            "amount",
            "payment_method",
            "payment_type",
            "reference_number",
            "gcash_number",
            "status",
            "payer_name",
            "payer_contact",
            "is_walk_in",
            "remarks",
            "item_name",
            "description",
            "date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "date", "created_at", "updated_at"]
        extra_kwargs = {
            "sale": {"required": False, "allow_null": True},
            "student": {"required": False, "allow_null": True},
            "payer_name": {"required": False, "allow_null": True},
            "payer_contact": {"required": False, "allow_null": True},
            "reference_number": {"required": False, "allow_null": True},
            "gcash_number": {"required": False, "allow_null": True},
            "remarks": {"required": False, "allow_null": True},
            "payment_type": {"required": False, "allow_null": True},
        }

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.first_name} {obj.student.last_name}"
        return None

    def get_payer_display_name(self, obj):
        if obj.is_walk_in:
            return obj.payer_name
        if obj.student:
            return f"{obj.student.first_name} {obj.student.last_name}"
        return obj.payer_name or "Unknown"

    def create(self, validated_data):
        item_name = validated_data.pop("item_name", None)
        description = validated_data.pop("description", None)

        remarks_parts = []
        if item_name:
            remarks_parts.append(item_name)
        if description:
            remarks_parts.append(description)

        existing_remarks = validated_data.get("remarks", "")
        if existing_remarks:
            if remarks_parts:
                validated_data["remarks"] = f"{existing_remarks} | " + " - ".join(remarks_parts)
            else:
                validated_data["remarks"] = existing_remarks
        elif remarks_parts:
            validated_data["remarks"] = " - ".join(remarks_parts)

        return super().create(validated_data)

class StudentChargeSerializer(serializers.ModelSerializer):
    """A student still owes for a specific item (created by a partial payment)."""

    student_name = serializers.SerializerMethodField()
    lrn = serializers.CharField(source="student.lrn", read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    # Writable on CREATE only, so the cashier can open a charge that is already
    # part-settled by the cash taken in that same transaction. The Payment row
    # for that cash is written by the cashier flow, so this must NOT create
    # another one (that would double-count revenue).
    initial_paid = serializers.DecimalField(
        max_digits=12, decimal_places=2, write_only=True, required=False
    )

    class Meta:
        model = StudentCharge
        fields = [
            "id",
            "student",
            "student_name",
            "lrn",
            "item_name",
            "qty",
            "unit_price",
            "total_amount",
            "amount_paid",
            "balance",
            "initial_paid",
            "source",
            "status",
            "notes",
            "reference_number",
            "created_at",
            "updated_at",
        ]
        # amount_paid and status are derived by the pay action so a client
        # cannot mark a charge paid without paying it.
        read_only_fields = ["id", "amount_paid", "status", "created_at", "updated_at"]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}".strip()

    def validate(self, attrs):
        qty = attrs.get("qty", getattr(self.instance, "qty", 1) or 1)
        unit_price = attrs.get("unit_price", getattr(self.instance, "unit_price", 0))
        if qty < 1:
            raise serializers.ValidationError({"qty": "Quantity must be at least 1."})
        if unit_price is None or unit_price < 0:
            raise serializers.ValidationError(
                {"unit_price": "Unit price cannot be negative."}
            )

        initial_paid = attrs.get("initial_paid")
        if initial_paid is not None:
            if self.instance is not None:
                raise serializers.ValidationError(
                    {
                        "initial_paid": (
                            "initial_paid only applies when the charge is created. "
                            "Use the pay action to settle it later."
                        )
                    }
                )
            if initial_paid < 0:
                raise serializers.ValidationError(
                    {"initial_paid": "initial_paid cannot be negative."}
                )
            total = (unit_price or 0) * (qty or 1)
            if initial_paid > total:
                raise serializers.ValidationError(
                    {
                        "initial_paid": (
                            f"initial_paid cannot exceed the total of {total}."
                        )
                    }
                )
        return attrs

    def create(self, validated_data):
        initial_paid = validated_data.pop("initial_paid", None) or 0
        charge = StudentCharge.objects.create(amount_paid=initial_paid, **validated_data)
        charge.recompute_status()
        charge.save(update_fields=["status"])
        return charge

