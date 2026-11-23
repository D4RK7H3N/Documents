from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal


class Terminal(models.Model):
    """A physical POS device.

    The Electron app sends a stable hardware id (X-Device-Id header) with
    every API call; unknown devices are auto-registered by middleware and
    renamed to "Terminal 1..N" by the admin. Revenue can then be broken down
    per register without touching any grand total.
    """

    device_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "device_id"]

    def __str__(self):
        return self.name or self.device_id


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
    # Which register recorded the sale (Electron X-Device-Id) and which staff
    # account was logged in. Both optional so old rows and browser sessions
    # stay valid and surface as "Unassigned" in revenue reports.
    terminal = models.ForeignKey(
        'sales.Terminal',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sales'
    )
    created_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sales'
    )
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


class Disbursement(models.Model):
    """An expense paid out of the register's cash during the day.

    Logged by the cashier as it happens (fare, supplies, ...); the daily
    collection report subtracts the day's disbursements from the total
    collection to arrive at the cash on hand.
    """

    date = models.DateField(default=timezone.now, db_index=True)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disbursements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]

    def __str__(self):
        return f"{self.description}: {self.amount} ({self.date})"


class DailyCashReport(models.Model):
    """Frozen end-of-day snapshot per cashier per date.

    `generated_at` is the exact moment the cashier pressed Generate — the
    clock is the cutoff. The window covered is
    (previous report's generated_at, generated_at], so money recorded after
    printing lands in the next report instead of vanishing between days.
    Collections, disbursements and denominations are snapshotted as JSON so a
    printed report never changes afterwards.
    """

    date = models.DateField(db_index=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_cash_reports",
    )
    period_start = models.DateTimeField()
    generated_at = models.DateTimeField()

    collections = models.JSONField(default=list)
    disbursements = models.JSONField(default=list)
    denominations = models.JSONField(default=dict)

    total_collection = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_disbursement = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    counted_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    difference = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["prepared_by", "date"]
        ordering = ["-date"]

    def __str__(self):
        who = self.prepared_by.username if self.prepared_by else "?"
        return f"Daily report {self.date} - {who}"
