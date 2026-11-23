from django.db import models
from decimal import Decimal


class Sale(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Fully Paid'),
        ('partial', 'Partially Paid'),
        ('unpaid', 'Unpaid'),
    ]

    # Use string reference instead of importing Student
    student = models.ForeignKey(
        'students.Student',  # String reference
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sales'
    )
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    # The customer-facing OR number, e.g. OR-20261015-00001. The cashier
    # mints this in the browser, so it has to be handed to the backend or the
    # sale is recorded with no reference and Revenue shows a blank.
    receipt_number = models.CharField(
        max_length=50, null=True, blank=True, db_index=True
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    gcash_number = models.CharField(max_length=20, blank=True, null=True)
    gcash_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def balance(self):
        """Calculate remaining balance"""
        return max(Decimal('0.00'), self.total - self.amount_paid)

    def update_payment_status(self):
        """Update payment status based on amount paid"""
        if self.amount_paid >= self.total:
            self.payment_status = 'paid'
        elif self.amount_paid > 0:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'unpaid'
        self.save()

    def __str__(self):
        if self.customer_name:
            return f"Sale #{self.id} - {self.customer_name}"
        if self.student:
            return f"Sale #{self.id} - {self.student.first_name} {self.student.last_name}"
        return f"Sale #{self.id} - Walk-in Customer"
    

class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        related_name="items",
        on_delete=models.CASCADE
    )
    # Product is now optional - null for custom items
    product = models.ForeignKey(
        'products.Product',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    # Custom item name (used when product is null)
    custom_item_name = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # Which size was sold, for sized products (uniforms). `variant` keeps the
    # link for stock tracking; `size` is a snapshot so the receipt still reads
    # correctly even if the variant row is later edited or deleted.
    variant = models.ForeignKey(
        'products.ProductVariant',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sale_items'
    )
    size = models.CharField(max_length=20, null=True, blank=True)

    @property
    def subtotal(self):
        return self.price * self.quantity

    @property
    def name(self):
        """Return product name or custom item name"""
        if self.product:
            return self.product.name
        return self.custom_item_name or 'Custom Item'

    @property
    def label(self):
        """Name plus size, for receipt and report lines."""
        return f"{self.name} ({self.size})" if self.size else self.name

    def get_item_name(self):
        """Return product name or custom item name (method version for template/view compatibility)"""
        return self.name

    def __str__(self):
        return f"{self.name} x {self.quantity}"