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
    # The fee is collected in four terms: 1st, 2nd, 3rd and Final.
    first_term = models.DecimalField(max_digits=10, decimal_places=2)
    second_term = models.DecimalField(max_digits=10, decimal_places=2)
    third_term = models.DecimalField(max_digits=10, decimal_places=2)
    final_term = models.DecimalField(max_digits=10, decimal_places=2)
    academic_year = models.CharField(max_length=9, help_text="e.g., 2024-2025")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'academic_year')
        ordering = ['-academic_year']
    
    @property
    def first_sem(self):
        return self.first_term + self.second_term
    
    @property
    def second_sem(self):
        return self.third_term + self.final_term
    
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
    # Which register (Electron X-Device-Id) and staff account recorded this
    # payment; NULL for old rows and browser sessions ("Unassigned").
    terminal = models.ForeignKey(
        'sales.Terminal',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tuition_payments'
    )
    created_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tuition_payments'
    )
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