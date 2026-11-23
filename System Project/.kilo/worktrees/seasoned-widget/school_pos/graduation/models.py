from django.db import models
from django.utils import timezone
from students.models import Student
from decimal import Decimal


class GraduationEvent(models.Model):
    """Graduation event/event details"""

    STATUS_CHOICES = [
        ('Planning', 'Planning'),
        ('Registration', 'Registration Open'),
        ('Closed', 'Registration Closed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    name = models.CharField(max_length=200, help_text="Event name (e.g., Grade 6 Graduation)")
    description = models.TextField(blank=True)

    event_date = models.DateField(help_text="Date of the graduation event")
    registration_deadline = models.DateField(help_text="Last day to register/pay fees")

    # Graduation Package Fee (single consolidated fee)
    graduation_package_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Graduation package fee per student (includes gown, diploma, ceremony, etc.)"
    )

    # Total calculated fee (kept for backward compatibility)
    total_fee_per_student = models.DecimalField(max_digits=10, decimal_places=2, editable=False, help_text="Total fee per student")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Planning')
    max_participants = models.IntegerField(default=0, help_text="Maximum number of graduates (0 = unlimited)")

    # Ceremony details
    venue = models.CharField(max_length=200, blank=True)
    time = models.TimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-event_date']
        verbose_name = 'Graduation Event'
        verbose_name_plural = 'Graduation Events'

    def __str__(self):
        return f"{self.name} - {self.event_date.strftime('%B %d, %Y')}"

    def save(self, *args, **kwargs):
        """Calculate total fee per student using graduation package fee"""
        self.total_fee_per_student = self.graduation_package_fee
        super().save(*args, **kwargs)

    def get_total_participants(self):
        """Get number of students registered for this event"""
        return self.participants.filter(status__in=['Registered', 'Partial', 'Paid']).count()

    def get_total_paid(self):
        """Get total amount paid for this event"""
        from django.db.models import Sum
        total = self.payments.aggregate(Sum('amount'))['amount__sum']
        return total or Decimal('0.00')

    def get_total_balance(self):
        """Get total outstanding balance for this event"""
        from django.db.models import Sum
        total = self.participants.aggregate(Sum('balance'))['balance__sum']
        return total or Decimal('0.00')

    def get_total_expected_revenue(self):
        """Get total expected revenue if all students pay"""
        return self.total_fee_per_student * self.get_total_participants()

    def has_slots_available(self):
        """Check if event has available slots"""
        if self.max_participants == 0:
            return True
        return self.get_total_participants() < self.max_participants

    def is_registration_open(self):
        """Check if registration is still open"""
        from django.utils import timezone
        return self.status == 'Registration' and timezone.now().date() <= self.registration_deadline


class StudentGraduation(models.Model):
    """Student enrollment/participation in a graduation event"""

    STATUS_CHOICES = [
        ('Registered', 'Registered'),
        ('Partial', 'Partially Paid'),
        ('Paid', 'Fully Paid'),
        ('Cancelled', 'Cancelled'),
    ]

    GRADUATION_LEVEL_CHOICES = [
        ('SHS', 'Senior High'),
        ('BUN', 'Bundled'),
        ('College', 'College'),
    ]

    graduation_event = models.ForeignKey(
        GraduationEvent,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='graduation_events'
    )

    graduation_level = models.CharField(max_length=10, choices=GRADUATION_LEVEL_CHOICES)
    section = models.CharField(max_length=100, blank=True, help_text="Class/Section name")

    registration_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Registered')

    # Financial tracking
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total fee for this student")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Graduation details
    honors_awarded = models.CharField(max_length=200, blank=True, help_text="e.g., With Honors, Valedictorian, etc.")
    special_awards = models.TextField(blank=True, help_text="Any special awards or recognition")

    # Documentation
    requirements_completed = models.BooleanField(default=False, help_text="All graduation requirements completed")
    noted_by = models.CharField(max_length=100, blank=True, help_text="Staff who noted requirements completion")

    notes = models.TextField(blank=True, help_text="Additional notes or remarks")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['graduation_event', 'student']
        ordering = ['-registration_date']
        verbose_name = 'Student Graduation Record'
        verbose_name_plural = 'Student Graduation Records'

    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name} - {self.graduation_event.name}"

    def save(self, *args, **kwargs):
        """Update balance and total fee on save"""
        if not self.total_fee and self.graduation_event:
            self.total_fee = self.graduation_event.total_fee_per_student
        self.balance = self.total_fee - self.amount_paid
        super().save(*args, **kwargs)
        self.update_status()

    def update_status(self):
        """Update payment status based on amount paid"""
        if self.amount_paid >= self.total_fee:
            self.status = 'Paid'
        elif self.amount_paid > 0:
            self.status = 'Partial'
        else:
            self.status = 'Registered'
        super().save(update_fields=['status', 'updated_at'])

    def get_payment_progress(self):
        """Calculate payment progress percentage"""
        if self.total_fee == 0:
            return 100
        progress = (self.amount_paid / self.total_fee) * 100
        return min(float(progress), 100)

    def get_payment_history(self):
        """Get all payments for this graduation record"""
        return self.payments.all().order_by('-payment_date')


class GraduationPayment(models.Model):
    """Payment for graduation event"""

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Check', 'Check'),
    ]

    student_graduation = models.ForeignKey(
        StudentGraduation,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    graduation_event = models.ForeignKey(
        GraduationEvent,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='graduation_payments'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)

    method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    reference_number = models.CharField(max_length=100, blank=True, help_text="Transaction ID, check number, etc.")
    gcash_number = models.CharField(max_length=20, blank=True, help_text="GCash number if paid via GCash")

    received_by = models.CharField(max_length=100, blank=True, help_text="Staff who received payment")
    remarks = models.TextField(blank=True, help_text="Additional remarks about the payment")

    # For audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['student', '-payment_date']),
            models.Index(fields=['graduation_event', '-payment_date']),
        ]
        verbose_name = 'Graduation Payment'
        verbose_name_plural = 'Graduation Payments'

    def __str__(self):
        return f"₱{self.amount:,.2f} - {self.student.first_name} {self.student.last_name}"

    def save(self, *args, **kwargs):
        """Update StudentGraduation balance when payment is saved"""
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Update the parent StudentGraduation record
        if self.student_graduation:
            # Calculate total paid for this student graduation
            from django.db.models import Sum
            total_paid = self.student_graduation.payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            self.student_graduation.amount_paid = total_paid
            self.student_graduation.save()
