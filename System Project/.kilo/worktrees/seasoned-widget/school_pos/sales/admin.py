from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "get_customer", "total", "created_at")
    inlines = [SaleItemInline]

    def get_customer(self, obj):
        if obj.customer_name:
            return obj.customer_name
        if obj.student:
            return f"{obj.student.first_name} {obj.student.last_name}"
        return "Walk-in Customer"
    get_customer.short_description = "Customer"
