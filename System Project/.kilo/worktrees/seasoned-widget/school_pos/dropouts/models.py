from django.db import models
from students.models import Student


class Dropout(models.Model):
    """Tracks dropout records with additional context beyond student status."""

    STATUS_CHOICES = [
        ("confirmed", "Confirmed"),
        ("reinstated", "Reinstated"),
    ]

    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='dropout_record'
    )
    dropout_date = models.DateField()
    # Where the student was when they dropped out. Captured separately from
    # Student.section/current_grade_level, which keep changing afterwards.
    last_grade_level = models.CharField(max_length=50, blank=True, null=True)
    last_section = models.CharField(max_length=100, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.CharField(max_length=200, blank=True, null=True)
    # Reinstatement used to DELETE this row, destroying the dropout history and
    # leaving nothing to distinguish a former dropout from a current one. The
    # record is now kept and flagged instead, so history survives and a
    # reinstated student becomes promotable again.
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="confirmed",
        help_text="'confirmed' blocks promotion; 'reinstated' is historical only.",
    )
    reinstated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-dropout_date']

    def __str__(self):
        return f"Dropout: {self.student.first_name} {self.student.last_name} ({self.dropout_date})"

    @property
    def is_active(self):
        """True while the student is currently dropped out."""
        return self.status == "confirmed"