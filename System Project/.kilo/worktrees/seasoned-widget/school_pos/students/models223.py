from django.db import models
from django.utils import timezone

class Student(models.Model):
    # 1. Personal Information
    lrn = models.CharField(max_length=20, unique=True) # Learner Reference Number
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=[("Male", "Male"), ("Female", "Female")],
        blank=True,
        null=True
    )
    nationality = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # 2. Family / Guardian Information
    guardian_name = models.CharField(max_length=200, blank=True, null=True)
    guardian_relationship = models.CharField(max_length=100, blank=True, null=True)
    guardian_contact = models.CharField(max_length=20, blank=True, null=True)
    guardian_occupation = models.CharField(max_length=100, blank=True, null=True)
    guardian_address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=200, blank=True, null=True)

    # 3. Academic Information
    previous_school = models.CharField(max_length=200, blank=True, null=True)
    last_grade_completed = models.CharField(max_length=50, blank=True, null=True)

    #  NEW: distinguish SHS vs College
    LEVEL_CHOICES = [
        ("SHS", "Senior High School"),
        ("COL", "College"),
        ("BUN", "Bundled")  # For Bundled students
    ]
    level_type = models.CharField(max_length=3, choices=LEVEL_CHOICES, default="SHS")

    #  SHS specific
    shs_grade = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=[("11", "Grade 11"), ("12", "Grade 12")]
    )

    #  College specific
    college_year = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("1", "1st Year"),
            ("2", "2nd Year"),
            ("3", "3rd Year"),
            ("4", "4th Year"),
        ]
    )

    # Keep your existing field (for backward compatibility)
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
        null=True
    )

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
        ],
        default="New"
    )
    payment_details = models.TextField(blank=True, null=True)
    scholarship_discount = models.TextField(blank=True, null=True)

    # 6. Other Data
    photo = models.ImageField(upload_to="students/photos/", blank=True, null=True)
    extracurricular = models.TextField(blank=True, null=True)

    # Tuition Balance
    tuition_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        if self.level_type == "SHS":
            return f"{self.lrn} - {self.last_name}, {self.first_name} (Grade {self.shs_grade})"
        elif self.level_type == "COL":
            return f"{self.lrn} - {self.last_name}, {self.first_name} (Year {self.college_year})"
        return f"{self.lrn} - {self.last_name}, {self.first_name}"
