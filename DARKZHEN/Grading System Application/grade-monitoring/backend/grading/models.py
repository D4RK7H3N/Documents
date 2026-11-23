from decimal import Decimal

from django.conf import settings
from django.db import models

from academics.models import ClassAssignment, StudentProfile, Subject

from . import engine


class GradingConfig(models.Model):
    name = models.CharField(max_length=100, default="DepEd Order 8, s. 2015")
    weights = models.JSONField(default=dict)
    transmutation_table = models.JSONField(default=list)
    is_active = models.BooleanField(default=False)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_active(cls):
        config = cls.objects.filter(is_active=True).first()
        if config is None:
            config = cls.objects.first()
        if config is None:
            config = cls.objects.create(
                weights=engine.DEFAULT_WEIGHTS,
                transmutation_table=engine.DEPED_TRANSMUTATION_TABLE,
                is_active=True,
            )
        return config

    def weights_for(self, subject_type):
        return self.weights.get(subject_type, self.weights.get("core", {}))


class Assessment(models.Model):
    class Component(models.TextChoices):
        WRITTEN_WORK = engine.WW, "Written Work"
        PERFORMANCE_TASK = engine.PT, "Performance Task"
        QUARTERLY_ASSESSMENT = engine.QA, "Quarterly Assessment"

    class_assignment = models.ForeignKey(ClassAssignment, on_delete=models.PROTECT, related_name="assessments")
    component = models.CharField(max_length=2, choices=Component.choices)
    quarter = models.PositiveSmallIntegerField(choices=[(1, "Q1"), (2, "Q2"), (3, "Q3"), (4, "Q4")])
    title = models.CharField(max_length=200)
    highest_possible_score = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["quarter", "component", "id"]
        indexes = [models.Index(fields=["class_assignment", "quarter"])]


class Score(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.PROTECT, related_name="scores")
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name="scores")
    raw_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["assessment", "student"], name="uniq_score_assessment_student")
        ]
        indexes = [models.Index(fields=["student"]), models.Index(fields=["assessment"])]


class QuarterGrade(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name="quarter_grades")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="quarter_grades")
    quarter = models.PositiveSmallIntegerField(choices=[(1, "Q1"), (2, "Q2"), (3, "Q3"), (4, "Q4")])
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    initial_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "subject", "quarter"], name="uniq_quarter_grade")
        ]
        indexes = [models.Index(fields=["student", "quarter"])]


class SemesterGrade(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name="semester_grades")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="semester_grades")
    semester = models.PositiveSmallIntegerField(choices=[(1, "S1"), (2, "S2")])
    final = models.PositiveSmallIntegerField(null=True, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "subject", "semester"], name="uniq_semester_grade")
        ]


class GeneralAverage(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name="general_averages")
    semester = models.PositiveSmallIntegerField(choices=[(1, "S1"), (2, "S2")])
    average = models.PositiveSmallIntegerField(null=True, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "semester"], name="uniq_general_average")
        ]


class QuarterLock(models.Model):
    class_assignment = models.ForeignKey(ClassAssignment, on_delete=models.PROTECT, related_name="quarter_locks")
    quarter = models.PositiveSmallIntegerField(choices=[(1, "Q1"), (2, "Q2"), (3, "Q3"), (4, "Q4")])
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    locked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["class_assignment", "quarter"], name="uniq_quarter_lock")
        ]


class GradeSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        RETURNED = "returned", "Returned"

    class_assignment = models.ForeignKey(ClassAssignment, on_delete=models.PROTECT, related_name="submissions")
    quarter = models.PositiveSmallIntegerField(choices=[(1, "Q1"), (2, "Q2"), (3, "Q3"), (4, "Q4")])
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submissions_sent"
    )
    submitted_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submissions_received"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)
    decision_note = models.TextField(blank=True)
    snapshot = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="submission_decisions"
    )

    class Meta:
        ordering = ["-created_at"]
