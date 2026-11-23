from django.db import models
from students.models import Student
from products.models import Product
from django.utils import timezone

class Sale(models.Model):
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.customer_name:
            return f"Sale {self.id} - {self.customer_name}"
        elif self.student:
            return f"Sale {self.id} - {self.student.name}"
        return f"Sale {self.id} - Walk-in Customer"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sale_items")
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.price * self.quantity

class TuitionPayment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="cashier_tuition_payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, default="Cash")  # Cash, GCash, Bank, etc.
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.student} - ₱{self.amount:.2f} on {self.date.strftime('%Y-%m-%d')}"