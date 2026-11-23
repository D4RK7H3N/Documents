from django.conf import settings
from django.db import models
from django.utils import timezone
from students.models import Student
from decimal import Decimal


class EducationalTour(models.Model):
    """Educational Tour/Trip"""
    TOUR_STATUS_CHOICES = [
        ('Planned', 'Planned'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200, help_text="Tour name (e.g., Baguio Educational Trip)")
    destination = models.CharField(max_length=200)
    tour_company = models.CharField(max_length=200, blank=True, help_text="Tour/Travel company name")  # NEW FIELD
    description = models.TextField(blank=True)
    
    tour_date = models.DateField()  
    return_date = models.DateField()
    
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total cost per student")
    
    # Optional breakdown
    transportation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    accommodation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    food_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    entrance_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=TOUR_STATUS_CHOICES, default='Planned')
    # The year level this tour is for ("SHS - Grade 11", "Bundled - 1st Year
    # Tesda Accredited", ...). It drives which students can be enrolled and
    # which sections are offered on the tour.
    grade_level = models.CharField(max_length=60, blank=True, null=True)
    max_participants = models.IntegerField(default=0, help_text="Maximum number of students (0 = unlimited)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-tour_date']
        verbose_name = 'Educational Tour'
        verbose_name_plural = 'Educational Tours'
    
    def __str__(self):
        return f"{self.name} - {self.tour_date.strftime('%B %d, %Y')}"
    
    def get_total_participants(self):
        """Get number of students enrolled in this tour"""
        return self.enrollments.count()
    
    def get_total_paid(self):
        """Get total amount paid for this tour"""
        from django.db.models import Sum
        return self.payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    def get_total_balance(self):
        """Get total outstanding balance for this tour"""
        from django.db.models import Sum
        return self.enrollments.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
    
    def has_slots_available(self):
        """Check if tour has available slots"""
        if self.max_participants == 0:
            return True
        return self.get_total_participants() < self.max_participants


class TourEnrollment(models.Model):
    """Student enrollment in an educational tour"""
    ENROLLMENT_STATUS_CHOICES = [
        ('Enrolled', 'Enrolled'),
        ('Partial', 'Partially Paid'),
        ('Paid', 'Fully Paid'),
        ('Cancelled', 'Cancelled'),
    ]
    
    tour = models.ForeignKey(EducationalTour, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='tour_enrollments')
    
    enrollment_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS_CHOICES, default='Enrolled')
    
    # Financial tracking
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Documentation
    parent_consent = models.BooleanField(default=False, help_text="Parent/Guardian consent received")
    medical_clearance = models.BooleanField(default=False, help_text="Medical clearance submitted")
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tour', 'student']
        ordering = ['-enrollment_date']
        verbose_name = 'Tour Enrollment'
        verbose_name_plural = 'Tour Enrollments'
    
    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name} - {self.tour.name}"
    
    def update_balance(self):
        """Update balance and status after payment"""
        self.balance = self.total_fee - self.amount_paid
        
        # Update status based on payment
        if self.amount_paid >= self.total_fee:
            self.status = 'Paid'
        elif self.amount_paid > 0:
            self.status = 'Partial'
        else:
            self.status = 'Enrolled'
        
        self.save()
    
    def get_payment_progress(self):
        """Calculate payment progress percentage"""
        total_fee = Decimal(str(self.total_fee)) if self.total_fee else Decimal('0')
        if total_fee == 0:
            return 100
        progress = (self.amount_paid / total_fee) * 100
        return min(float(progress), 100)  # Cap at 100%


class TourPayment(models.Model):
    """Payment for educational tour"""
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('GCash', 'GCash'),
    ]
    
    enrollment = models.ForeignKey(TourEnrollment, on_delete=models.CASCADE, related_name='payments')
    tour = models.ForeignKey(EducationalTour, on_delete=models.CASCADE, related_name='payments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='tour_payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    
    method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    reference_number = models.CharField(max_length=100, blank=True, help_text="Transaction ID, check number, etc.")
    
    received_by = models.CharField(max_length=100, blank=True, help_text="Staff who received payment")
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="tour_payments_recorded",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Tour Payment'
        verbose_name_plural = 'Tour Payments'
    
    def __str__(self):
        return f"{self.student} - PHP {self.amount:.2f} - {self.payment_date.strftime('%B %d, %Y')}"
    
    def save(self, *args, **kwargs):
        """Update enrollment balance after payment is created"""
        super().save(*args, **kwargs)
        
        # Recalculate enrollment amount paid
        self.enrollment.amount_paid = self.enrollment.payments.aggregate(
            models.Sum('amount')
        )['amount__sum'] or Decimal('0.00')
        
        # Update balance and status
        self.enrollment.update_balance()