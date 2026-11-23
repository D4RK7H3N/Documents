from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, related_name="products", on_delete=models.PROTECT
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    # Semantic search vector for (title + description + category),
    # stored as a JSON list of floats (pgvector can replace this later).
    embedding = models.JSONField(null=True, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    """A purchasable variant of a product with its own stock (and optional
    price override), e.g. Color=Black."""

    product = models.ForeignKey(
        Product, related_name="variants", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)  # option name, e.g. "Color"
    value = models.CharField(max_length=100)  # option value, e.g. "Black"
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Leave empty to use the product price",
    )
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = [("product", "name", "value")]
        ordering = ["name", "value"]

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.price


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    image = models.FileField(upload_to="products/")
    alt = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "id"]

    def __str__(self):
        return f"Image for {self.product.name}"


class Review(models.Model):
    SENTIMENT_CHOICES = [
        ("positive", "Positive"),
        ("neutral", "Neutral"),
        ("negative", "Negative"),
    ]

    product = models.ForeignKey(
        Product, related_name="reviews", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        "auth.User", related_name="reviews", on_delete=models.CASCADE
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    sentiment = models.CharField(
        max_length=16, choices=SENTIMENT_CHOICES, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("product", "user")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review {self.rating}/5 for {self.product.name} by {self.user}"
