from django.db import models
from django.utils import timezone
from students.models import Student


class TuitionPayment(models.Model):
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name="cashier_tuition_payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, default="Cash")
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} - ₱{self.amount:.2f} on {self.date.strftime('%Y-%m-%d')}"