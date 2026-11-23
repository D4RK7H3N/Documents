from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator

import os
import uuid


# Module-level so Django can serialize them into migrations (a closure or
# nested function cannot be). Media is served unauthenticated (see
# school_pos.urls serve_media), so the original filename must never become
# part of the public URL: predictable names like `juan.jpg` under a guessable
# date folder would let anyone download student photos and documents without
# logging in.
def _student_photo_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"students/photos/{uuid.uuid4().hex}{ext}"


def _student_document_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"student_documents/{uuid.uuid4().hex}{ext}"


class Student(models.Model):
    # 1. Personal Information
    lrn = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=[("Male", "Male"), ("Female", "Female")],
        blank=True,
        null=True,
    )
    nationality = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # 2. Family / Guardian Information
    guardian_name = models.CharField(max_length=200, blank=True, null=True)
    guardian_relationship = models.CharField(max_length=100, blank=True, null=True)
    guardian_contact = models.CharField(max_length=20, blank=True, null=True)
    guardian_no = models.CharField(max_length=50, blank=True, null=True, help_text="Guardian's ID number or contact number")
    guardian_occupation = models.CharField(max_length=100, blank=True, null=True)
    guardian_address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=200, blank=True, null=True)

    # 3. Academic Information
    previous_school = models.CharField(max_length=200, blank=True, null=True)
    last_grade_completed = models.CharField(max_length=50, blank=True, null=True)
    is_als_graduate = models.BooleanField(default=False)

    LEVEL_CHOICES = [
        ("SHS", "Senior High School"),
        ("COL", "College"),
        ("BUN", "Bundled"),
    ]
    level_type = models.CharField(max_length=3, choices=LEVEL_CHOICES, default="SHS")

    shs_grade = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=[("11", "Grade 11"), ("12", "Grade 12")],
    )

    college_year = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("1", "1st Year"),
            ("2", "2nd Year"),
            ("3", "3rd Year"),
            ("4", "4th Year"),
        ],
    )

    current_grade_level = models.CharField(
        max_length=50,
        choices=[
            ("Grade 11", "Grade 11"),
            ("Grade 12", "Grade 12"),
            ("College 1st Year", "College 1st Year"),
            ("College 2nd Year", "College 2nd Year"),
            ("College 3rd Year", "College 3rd Year"),
            ("College 4th Year", "College 4th Year"),
        ],
        blank=True,
        null=True,
    )

    track_strand = models.CharField(max_length=100, blank=True, null=True)
    # ForeignKey to the new Strand model for better track/strand management
    strand = models.ForeignKey(
        "tracks.Strand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    course_fk = models.ForeignKey(
        "tracks.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
        verbose_name="Course",
    )
    section = models.CharField(max_length=50, blank=True, null=True)
    # Audit trail for bulk section assignment. Bulk assign rewrites academic
    # placement in one shot, so we record who did it and when.
    section_assigned_by = models.CharField(max_length=150, blank=True, null=True)
    section_assigned_at = models.DateTimeField(blank=True, null=True)
    course = models.CharField(max_length=200, blank=True, null=True)
    section_strand_course = models.CharField(max_length=200, blank=True, null=True)
    academic_records = models.TextField(blank=True, null=True)

    # 4. Health Information
    medical_conditions = models.TextField(blank=True, null=True)
    blood_type = models.CharField(max_length=3, blank=True, null=True)
    immunization_records = models.TextField(blank=True, null=True)
    preferred_hospital = models.CharField(max_length=200, blank=True, null=True)
    health_insurance = models.CharField(max_length=200, blank=True, null=True)

    # 5. Enrollment Details
    date_of_enrollment = models.DateField(default=timezone.now)
    enrollment_status = models.CharField(
        max_length=20,
        choices=[
            ("New", "New"),
            ("Continuing", "Continuing"),
            ("Transferee", "Transferee"),
            ("ALS Graduate", "ALS Graduate"),
        ],
        default="New",
    )
    student_type = models.CharField(
        max_length=20,
        choices=[
            ("Payee", "Payee"),
            ("Regular", "Regular"),
        ],
        default="Payee",
        help_text="Regular = No tuition (for SHS continuing students), Payee = Has tuition",
    )
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Drop-out", "Drop-out"),
        ("Transferred", "Transferred"),
        ("Graduated", "Graduated"),
    ]
    BILLING_CATEGORY_CHOICES = [
        ("Regular", "Regular (Non-ESC / Voucher)"),
        ("ESC", "ESC (Senior High)"),
        ("Discounted", "Discounted / Scholar"),
        ("Complementary", "Complementary"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")
    # School year the student is currently enrolled in (e.g. "2026-2027").
    # The tuition ledger is kept per school year, so the student's own year
    # has to be recorded too - it used to be written on the record but never
    # stored, because the field did not exist.
    school_year = models.CharField(max_length=20, blank=True, null=True)
    # School year the student graduated in (e.g. "2021-2022"). Set when the
    # student is marked Graduated so staff can look a graduate up per S.Y.
    graduated_sy = models.CharField(max_length=20, blank=True, null=True)
    # Class adviser, shown on the cashier settlement panel.
    adviser = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Class adviser",
    )
    # Drives the "Billing / Category" row on the cashier settlement panel.
    billing_category = models.CharField(
        max_length=20,
        choices=BILLING_CATEGORY_CHOICES,
        default="Regular",
        help_text="Billing category",
    )
    payment_details = models.TextField(blank=True, null=True)
    scholarship_discount = models.TextField(blank=True, null=True)

    # 6. Other Data
    photo = models.ImageField(upload_to=_student_photo_upload_to, blank=True, null=True)
    extracurricular = models.TextField(blank=True, null=True)

    # 7. Tuition Information
    tuition_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    custom_tuition_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    def display_level(self):
        if self.level_type == "SHS":
            return f"Grade {self.shs_grade}" if self.shs_grade else "Senior High"
        if self.level_type == "COL":
            return f"Year {self.college_year}" if self.college_year else "College"
        if self.level_type == "BUN":
            if self.college_year:
                return f"Bundled Year {self.college_year}"
            return f"Bundled College" if self.college_year else "Bundled College"
        if self.current_grade_level:
            return self.current_grade_level
        return "N/A"

    def __str__(self):
        return f"{self.lrn} - {self.last_name}, {self.first_name}"


class StudentDocument(models.Model):
    """Store student documents like PSA, photos, report cards, etc."""

    DOCUMENT_TYPE_CHOICES = [
        ("PSA", "PSA Birth Certificate"),
        ("PHOTO_2x2", "2x2 Photo"),
        ("PHOTO_4x6", "4x6 Photo"),
        ("REPORT_CARD_G10", "Grade 10 Report Card"),
        ("REPORT_CARD_G11", "Grade 11 Report Card"),
        ("REPORT_CARD_G12", "Grade 12 Report Card"),
        ("FORM_137", "Form 137 (Permanent Record)"),
        ("GOOD_MORAL", "Certificate of Good Moral"),
        ("VACCINATION", "Vaccination Record"),
        ("CLEARANCE", "School Clearance"),
        ("ID_VALID", "Valid ID"),
        ("MEDICAL", "Medical/Health Record"),
        ("OTHER", "Other Document"),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(
        upload_to=_student_document_upload_to,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "jpg", "jpeg", "png", "doc", "docx"]
            )
        ],
    )
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_documents",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.get_document_type_display()}"

    class Meta:
        db_table = "student_document"
        ordering = ["-uploaded_at"]
        unique_together = ["student", "document_type"]


class StudentData(models.Model):
    """Store additional student enrollment data"""

    BLOOD_TYPE_CHOICES = [
        ("O+", "O+"),
        ("O-", "O-"),
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
    ]

    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="enrollment_data"
    )
    enrollment_date = models.DateField(auto_now_add=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    health_concerns = models.TextField(blank=True)
    blood_type_choice = models.CharField(
        max_length=3, blank=True, choices=BLOOD_TYPE_CHOICES, verbose_name="Blood Type"
    )
    psa_submitted = models.BooleanField(default=False)
    photos_submitted = models.BooleanField(default=False)
    report_card_submitted = models.BooleanField(default=False)
    form_137_submitted = models.BooleanField(default=False)
    good_moral_submitted = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    is_complete = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - Enrollment Data"

    def check_required_documents(self):
        """Check if all required documents are submitted"""
        required_docs = ["PSA", "PHOTO_2x2", "REPORT_CARD_G10"]
        submitted_docs = self.student.documents.filter(
            document_type__in=required_docs
        ).values_list("document_type", flat=True)
        return all(doc in submitted_docs for doc in required_docs)

    class Meta:
        db_table = "student_enrollment_data"
        ordering = ["-updated_at"]
