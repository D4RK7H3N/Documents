from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Section(models.Model):
    class GradeLevel(models.TextChoices):
        G11 = "Grade 11", "Grade 11"
        G12 = "Grade 12", "Grade 12"

    name = models.CharField(max_length=50)
    school_year = models.CharField(max_length=9)
    grade_level = models.CharField(
        max_length=10, choices=GradeLevel.choices, default=GradeLevel.G12
    )

    class Meta:
        ordering = ["school_year", "grade_level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "school_year", "grade_level"], name="uniq_section_name_year_level"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.grade_level})"


class Subject(models.Model):
    class SubjectType(models.TextChoices):
        CORE = "core", "Core"
        APPLIED = "applied", "Applied"
        SPECIALIZED = "specialized", "Specialized"

    name = models.CharField(max_length=100)
    subject_type = models.CharField(max_length=12, choices=SubjectType.choices, default=SubjectType.CORE)
    weights_override = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClassAssignment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="class_assignments")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="class_assignments")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="class_assignments"
    )
    school_year = models.CharField(max_length=9)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "section", "school_year"], name="uniq_assignment_subject_section_year"
            )
        ]

    def __str__(self):
        return f"{self.subject.name} - {self.section.name}"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student_profile"
    )
    lrn = models.CharField(
        max_length=12,
        unique=True,
        validators=[RegexValidator(regex=r"^\d{12}$", message="LRN must be exactly 12 digits.")],
    )
    full_name = models.CharField(max_length=150)
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="students")

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name
