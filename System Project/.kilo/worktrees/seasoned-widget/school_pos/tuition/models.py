from django.db import models
from django.utils import timezone


class TuitionFeeStructure(models.Model):
    LEVEL_CHOICES = [
        ("SHS", "Senior High School"),
        ("COL", "College"),
        ("BUN", "Bundled"),
    ]

    level_type = models.CharField(max_length=3, choices=LEVEL_CHOICES, unique=True)
    base_fee = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date"]

    def __str__(self):
        return f"{self.get_level_type_display()} - ₱{self.base_fee:,.2f}"


class TuitionBreakdown(models.Model):
    # ✅ USE STRING REFERENCE - NO IMPORT
    student = models.OneToOneField(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='tuition_breakdown'
    )
    first_quarter = models.DecimalField(max_digits=10, decimal_places=2)
    second_quarter = models.DecimalField(max_digits=10, decimal_places=2)
    third_quarter = models.DecimalField(max_digits=10, decimal_places=2)
    fourth_quarter = models.DecimalField(max_digits=10, decimal_places=2)
    academic_year = models.CharField(max_length=9, help_text="e.g., 2024-2025")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'academic_year')
        ordering = ['-academic_year']
    
    @property
    def first_sem(self):
        return self.first_quarter + self.second_quarter
    
    @property
    def second_sem(self):
        return self.third_quarter + self.fourth_quarter
    
    @property
    def total(self):
        return self.first_sem + self.second_sem
    
    def __str__(self):
        return f"Breakdown for {self.student} - {self.academic_year}"


class TuitionPayment(models.Model):
    METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Credit/Debit Card', 'Credit/Debit Card'),
        ('Check', 'Check'),
    ]
    
    # ✅ USE STRING REFERENCE - NO IMPORT
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='tuition_payments'
    )
    school_year = models.CharField(max_length=9, default="2024-2025", help_text="e.g., 2024-2025")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, choices=METHOD_CHOICES)
    gcash_number = models.CharField(max_length=50, blank=True, null=True)
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    reference_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['student', '-date']),
            models.Index(fields=['method']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        return f"Payment #{self.id} - {self.student} - ₱{self.amount:,.2f}"