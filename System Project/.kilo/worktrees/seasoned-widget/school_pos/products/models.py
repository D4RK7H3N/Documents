from django.db import models


class Product(models.Model):
    """A sellable item at the cashier counter.

    Was previously conflated with tuition line items, so `tuition_type` held
    billing periods (Quarter / Semester / Other) and was required. It is now
    `category`, with the same two buckets the cashier UI groups by.
    """

    CATEGORY_CHOICES = [
        ("academic", "Academic"),
        ("products", "Product & Supplies"),
    ]

    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(null=True, blank=True)  # null = no stock tracking
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="products",
        help_text="Groups the item on the cashier checkout tabs.",
    )
    # Uniforms and other apparel. When set, the cashier asks for a size and
    # sells ProductVariant rows instead of the Product itself, so each size
    # carries its own stock and can be marked out independently.
    is_sized = models.BooleanField(
        default=False,
        help_text="Item comes in sizes - the cashier will ask which one.",
    )

    def __str__(self):
        return self.name

    @property
    def is_academic(self):
        return self.category == "academic"

    @property
    def total_stock(self):
        """Stock across every size, or the product's own stock when unsized."""
        if not self.is_sized:
            return self.stock
        return sum(v.stock or 0 for v in self.variants.all())


class ProductVariant(models.Model):
    """One size of a sized product, e.g. Product 'Uniform Set' / size 'M'."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    size = models.CharField(max_length=20)
    stock = models.IntegerField(null=True, blank=True)  # null = not tracked
    # Optional per-size price override; falls back to Product.price when null.
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave blank to use the parent product's price.",
    )

    class Meta:
        ordering = ["size"]
        unique_together = ["product", "size"]

    def __str__(self):
        return f"{self.product.name} - {self.size}"

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.price