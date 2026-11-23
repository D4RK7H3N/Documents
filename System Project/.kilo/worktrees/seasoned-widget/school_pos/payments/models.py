from django.db import models
from django.utils import timezone


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('Cash', 'Cash'),
        ('Card', 'Credit/Debit Card'),
        ('GCash', 'GCash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Check', 'Check'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # USE STRING REFERENCES - NO IMPORTS
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='Cash')
    payment_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Type: Miscellaneous, Laboratory, Assessment, Other"
    )
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    gcash_number = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='completed')
    payer_name = models.CharField(max_length=200, blank=True, null=True)
    payer_contact = models.CharField(max_length=50, blank=True, null=True)
    is_walk_in = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['status', '-date']),
            models.Index(fields=['student']),
        ]

    def __str__(self):
        if self.student:
            return f"Payment #{self.id} - {self.student} - ₱{self.amount:,.2f}"
        elif self.sale:
            return f"Payment #{self.id} - Sale #{self.sale.id} - ₱{self.amount:,.2f}"
        return f"Payment #{self.id} - ₱{self.amount:,.2f}"


class StudentCharge(models.Model):
    """An amount a student still owes for a specific item.

    Created when the cashier collects a partial ("Half") payment. Payment rows
    record money actually taken; this records what is still owed, and how much
    of it has been settled, so a charge can be part-paid over time.

    `source` decides how the balance is counted:
      * 'item'   - tuition_balance knows nothing about it, so the balance is
                   added to the student's outstanding total.
      * 'tuition' - Student.tuition_balance already reflects money taken
                   against tuition, so this balance is DISPLAYED but never
                   added again, otherwise the total would double-count.
    """

    SOURCE_CHOICES = [
        ('item', 'Item'),
        ('tuition', 'Tuition'),
    ]
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ]

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='charges',
    )
    item_name = models.CharField(max_length=200)
    qty = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='item')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    notes = models.TextField(blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['source', 'status']),
        ]

    @property
    def total_amount(self):
        return (self.unit_price or 0) * (self.qty or 0)

    @property
    def balance(self):
        return max(self.total_amount - (self.amount_paid or 0), 0)

    def recompute_status(self):
        """Derive status from the money actually paid."""
        balance = self.balance
        if balance <= 0:
            self.status = 'paid'
        elif (self.amount_paid or 0) > 0:
            self.status = 'partial'
        else:
            self.status = 'unpaid'
        return self.status

    def __str__(self):
        return f"{self.item_name} x{self.qty} - balance ₱{self.balance:,.2f} ({self.student})"