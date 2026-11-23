from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Cart(models.Model):
    user = models.OneToOneField(User, related_name="cart", on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "catalog.Product", related_name="cart_items", on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        related_name="cart_items",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def unit_price(self):
        if self.variant_id and self.variant.price is not None:
            return self.variant.price
        return self.product.price

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_METHOD_CHOICES = [("cod", "Cash on delivery"), ("paymongo", "PayMongo")]
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
    ]

    number = models.CharField(max_length=24, unique=True)
    user = models.ForeignKey(User, related_name="orders", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(
        max_length=16, choices=PAYMENT_METHOD_CHOICES, default="cod"
    )
    payment_status = models.CharField(
        max_length=16, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_name = models.CharField(max_length=120)
    shipping_phone = models.CharField(max_length=32)
    shipping_address = models.CharField(max_length=255)
    shipping_city = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=16)
    notes = models.TextField(blank=True)
    paymongo_session_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} ({self.user})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "catalog.Product", related_name="order_items", on_delete=models.PROTECT
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        related_name="order_items",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    product_name = models.CharField(max_length=200)
    variant_label = models.CharField(max_length=200, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
