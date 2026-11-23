from django.contrib import admin
from django.utils.html import format_html

from .models import Product, ProductVariant


class ProductVariantInline(admin.TabularInline):
    """Edit a sized product's sizes directly on its page."""

    model = ProductVariant
    extra = 1
    fields = ("size", "price", "stock")
    ordering = ("size",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "size", "effective_price_display", "stock")
    list_filter = ("product",)
    search_fields = ("product__name", "size")

    def effective_price_display(self, obj):
        return obj.effective_price

    effective_price_display.short_description = "Price"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "price", "stock", "size_summary",
        "colored_category", "is_sized",
    )
    list_filter = ("category", "is_sized")
    search_fields = ("name", "variants__size")
    list_editable = ("price", "stock")
    fields = ("name", "category", "is_sized", "price", "stock")
    list_per_page = 50
    inlines = [ProductVariantInline]

    def colored_category(self, obj):
        colors = {"academic": "blue", "products": "green"}
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.category, "black"),
            obj.get_category_display(),
        )

    colored_category.short_description = "Category"
    colored_category.admin_order_field = "category"

    def size_summary(self, obj):
        """Show the stocked sizes so the changelist is readable at a glance."""
        if not obj.is_sized:
            return format_html('<span style="color:#999;">—</span>')
        sizes = list(obj.variants.all())
        if not sizes:
            return format_html('<span style="color:#f85149;">no sizes set</span>')
        bits = []
        for v in sizes:
            colour = "#f85149" if (v.stock or 0) <= 0 else "#0f766e"
            suffix = f' ({v.stock})' if v.stock is not None else ''
            bits.append(
                f'<span style="color:{colour};font-weight:600;">{v.size}{suffix}</span>'
            )
        return format_html(" / ".join(bits))

    size_summary.short_description = "Sizes"