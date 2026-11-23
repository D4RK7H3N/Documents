from django.db import models
from django.core.exceptions import ValidationError
from students.models import Student

class DormBuilding(models.Model):
    """Represents a dormitory building"""
    GENDER_CHOICES = [
        ('Male', 'Boys Dormitory'),
        ('Female', 'Girls Dormitory'),
        ('Mixed', 'Mixed Dormitory'),
    ]
    
    name = models.CharField(max_length=100)
    gender_restriction = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default='Mixed',
        help_text="Restrict this building to specific gender"
    )
    total_rooms = models.IntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_gender_restriction_display()})"
    
    def available_rooms_count(self):
        """Count rooms that are not at full capacity"""
        return sum(1 for room in self.rooms.all() if room.has_space())
    
    class Meta:
        db_table = 'dorm_building'
        ordering = ['name']


class DormRoom(models.Model):
    """Represents individual rooms in a dorm"""
    ROOM_TYPE_CHOICES = [
        ('Single', 'Single'),
        ('Double', 'Double'),
        ('Quad', 'Quad'),
        ('Suite', 'Suite'),
    ]
    
    building = models.ForeignKey(DormBuilding, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=20)
    capacity = models.IntegerField(default=4)
    room_type = models.CharField(
        max_length=50,
        choices=ROOM_TYPE_CHOICES,
        default='Double'
    )
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.building.name} - Room {self.room_number}"
    
    def current_occupants(self):
        """Count active assignments"""
        return self.assignments.filter(status='Active').count()
    
    def has_space(self):
        """Check if room has available space"""
        return self.current_occupants() < self.capacity
    
    def occupancy_status(self):
        """Return occupancy status as string"""
        current = self.current_occupants()
        if current == 0:
            return "Empty"
        elif current < self.capacity:
            return "Available"
        else:
            return "Full"
    
    class Meta:
        db_table = 'dorm_room'
        unique_together = ('building', 'room_number')
        ordering = ['building', 'room_number']


class DormAssignment(models.Model):
    """Tracks student dorm assignments"""
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Terminated', 'Terminated'),
        ('Suspended', 'Suspended'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='dorm_assignments')
    room = models.ForeignKey(DormRoom, on_delete=models.CASCADE, related_name='assignments')
    date_started = models.DateField()
    date_ended = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Active'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.student} - {self.room} ({self.status})"
    
    def clean(self):
        """Validate gender restrictions"""
        # Only validate if room has gender restriction
        if self.room.building.gender_restriction != 'Mixed':
            # Check if student gender matches building restriction
            if hasattr(self.student, 'gender') and self.student.gender:
                if self.room.building.gender_restriction != self.student.gender:
                    raise ValidationError(
                        f"Gender mismatch: This building is restricted to "
                        f"{self.room.building.get_gender_restriction_display()}. "
                        f"Student gender: {self.student.gender}"
                    )
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    def total_paid(self):
        """Calculate total amount paid"""
        return sum(p.amount for p in self.payments.all())
    
    class Meta:
        db_table = 'dorm_assignment'
        ordering = ['-date_started']


class DormPayment(models.Model):
    """Records dorm fee payments"""
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Check', 'Check'),
        ('Online Payment', 'Online Payment'),
    ]
    
    assignment = models.ForeignKey(DormAssignment, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month_covered = models.CharField(max_length=20)
    year_covered = models.IntegerField()
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        default='Cash'
    )
    receipt_number = models.CharField(max_length=50, unique=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    def __str__(self):
        return f"{self.receipt_number} - ₱{self.amount}"
    
    class Meta:
        db_table = 'dorm_payment'
        ordering = ['-payment_date']