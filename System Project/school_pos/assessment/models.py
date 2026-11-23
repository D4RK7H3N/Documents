from django.conf import settings
from django.db import models
from django.utils import timezone
from students.models import Student
from decimal import Decimal


class AssessmentType(models.Model):
    """
    Types of assessments/fees beyond regular tuition
    Examples: Bartending, Automotive, COE, CSS, Lab Fees, etc.
    """
    CATEGORY_CHOICES = [
        ('NCII', 'NC II Certification'),
        ('LAB', 'Laboratory Fee'),
        ('MISC', 'Miscellaneous Fee'),
        ('CERT', 'Certificate/Document'),
        ('EXAM', 'Examination Fee'),
    ]
    
    APPLICABLE_TO_CHOICES = [
        ('SHS', 'Senior High School'),
        ('BUN', 'Bundled College'),
        ('COL', 'Regular College'),
        ('ALL', 'All Levels'),
    ]
    
    name = models.CharField(max_length=200, help_text="e.g., Bartending NC II, Automotive NC II")
    code = models.CharField(max_length=50, unique=True, help_text="Short code (e.g., BART, AUTO, CSS)")
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='NCII')
    
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Standard fee amount")
    
    applicable_to = models.CharField(
        max_length=3, 
        choices=APPLICABLE_TO_CHOICES, 
        default='ALL',
        help_text="Which student level this applies to"
    )
    
    # Optional: Link to specific tracks/strands
    applicable_tracks = models.CharField(
        max_length=500, 
        blank=True,
        help_text="Comma-separated tracks (e.g., ICT, Industrial)"
    )
    
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False, help_text="Required for graduation/certification")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - ₱{self.amount}"
    
    def get_applicable_display(self):
        """Human-readable applicable levels"""
        if self.applicable_tracks:
            return f"{self.get_applicable_to_display()} ({self.applicable_tracks})"
        return self.get_applicable_to_display()


class StudentAssessment(models.Model):
    """
    Individual student's assessment/fee assignment
    Links a student to a specific assessment type
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending Payment'),
        ('Partial', 'Partially Paid'),
        ('Paid', 'Fully Paid'),
        ('Waived', 'Waived/Exempted'),
        ('Cancelled', 'Cancelled'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assessments')
    assessment_type = models.ForeignKey(AssessmentType, on_delete=models.PROTECT, related_name='student_assessments')
    
    # Financial tracking
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # Dates
    date_assessed = models.DateTimeField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True, help_text="Optional payment deadline")
    
    # Notes and remarks
    notes = models.TextField(blank=True, help_text="Special notes or conditions")
    assessed_by = models.CharField(max_length=100, blank=True, help_text="Staff who created this assessment")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_assessed']
        unique_together = ['student', 'assessment_type']  # One assessment type per student
    
    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name} - {self.assessment_type.name}"
    
    def update_balance(self):
        """Update balance after payment"""
        self.balance = self.total_fee - self.amount_paid
        
        # Update status based on payment
        if self.amount_paid >= self.total_fee:
            self.status = 'Paid'
        elif self.amount_paid > 0:
            self.status = 'Partial'
        else:
            self.status = 'Pending'
        
        self.save()
    
    def get_payment_progress(self):
        """Calculate payment progress percentage"""
        from decimal import Decimal
        total = Decimal(str(self.total_fee)) if self.total_fee else Decimal('0')
        paid = Decimal(str(self.amount_paid)) if self.amount_paid else Decimal('0')
        if total == 0:
            return 100
        return float((paid / total) * 100)


class AssessmentPayment(models.Model):
    """
    Individual payment transaction for an assessment
    """
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Credit/Debit Card', 'Credit/Debit Card'),
    ]
    
    assessment = models.ForeignKey(StudentAssessment, on_delete=models.CASCADE, related_name='payments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assessment_payments')
    assessment_type = models.ForeignKey(AssessmentType, on_delete=models.PROTECT, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    reference_number = models.CharField(max_length=100, blank=True)
    gcash_number = models.CharField(max_length=20, blank=True)
    
    received_by = models.CharField(max_length=100, blank=True, help_text="Cashier/staff who received payment")
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assessment_payments_recorded",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.student} - {self.assessment_type.code} - ₱{self.amount}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update assessment balance after payment
        self.assessment.amount_paid = self.assessment.payments.aggregate(
            models.Sum('amount')
        )['amount__sum'] or 0
        self.assessment.update_balance()


class AssessmentBatch(models.Model):
    """
    Batch assignment of assessments to multiple students
    Useful for assigning fees to entire sections/tracks
    """
    name = models.CharField(max_length=200, help_text="e.g., ICT G11 Bartending NC II - SY 2024-2025")
    assessment_type = models.ForeignKey(AssessmentType, on_delete=models.PROTECT)
    
    # Filter criteria
    level_type = models.CharField(max_length=3, choices=[('SHS', 'SHS'), ('BUN', 'Bundled'), ('COL', 'College')])
    track_strand = models.CharField(max_length=100, blank=True, help_text="Specific track/strand")
    section = models.CharField(max_length=50, blank=True, help_text="Specific section")
    
    # Batch details
    students_count = models.IntegerField(default=0, help_text="Number of students assessed")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Assessment Batches'
    
    def __str__(self):
        return f"{self.name} ({self.students_count} students)"
