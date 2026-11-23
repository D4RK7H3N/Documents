import logging

from django.contrib import admin
from django.db.models import Avg
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import path

from .models import Category, Product, ProductImage, ProductVariant, Review

logger = logging.getLogger(__name__)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "product_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    change_list_template = "admin/catalog/product_change_list.html"
    list_display = (
        "name", "category", "price", "stock", "is_active", "is_featured",
        "has_embedding", "average_rating",
    )
    list_filter = ("category", "is_active", "is_featured")
    list_editable = ("price", "stock", "is_active", "is_featured")
    search_fields = ("name", "brand", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, ProductVariantInline]

    def has_embedding(self, obj):
        return obj.embedding is not None

    has_embedding.boolean = True
    has_embedding.short_description = "embedded"

    def average_rating(self, obj):
        result = obj.reviews.aggregate(v=Avg("rating"))["v"]
        return round(result, 1) if result is not None else "-"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "ai-describe/",
                self.admin_site.admin_view(self.ai_describe_view),
                name="catalog_product_ai_describe",
            ),
        ]
        return custom + urls

    def ai_describe_view(self, request):
        """Admin page: generate a product description draft with the LLM."""
        from ai import services
        from ai.services import LLMError, LLMNotConfiguredError

        name = ""
        features = ""
        draft = None
        error = None

        if request.method == "POST":
            name = request.POST.get("name", "").strip()
            features = request.POST.get("features", "").strip()
            if not name:
                error = "Product name is required."
            else:
                try:
                    draft = services.generate_description(name, features)
                except LLMNotConfiguredError as exc:
                    error = str(exc)
                except LLMError as exc:
                    error = f"LLM request failed: {exc}"

        context = {
            **self.admin_site.each_context(request),
            "title": "AI description generator",
            "name": name,
            "features": features,
            "draft": draft,
            "error": error,
        }
        return TemplateResponse(request, "admin/catalog/product_describe.html", context)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "sentiment", "created_at")
    list_filter = ("sentiment", "rating")
    search_fields = ("product__name", "user__username", "comment")
    readonly_fields = ("product", "user", "rating", "comment", "sentiment", "created_at")
