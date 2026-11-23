from django.contrib import admin
from .models import Sale, SaleItem, Terminal


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    """Rename auto-registered devices to "Terminal 1..N" here."""
    list_display = ("name", "device_id", "registered_at", "last_seen_at", "is_active")
    list_display_links = ("name",)
    list_editable = ("is_active",)
    search_fields = ("name", "device_id")


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "get_customer", "total", "get_terminal", "get_staff", "created_at")
    inlines = [SaleItemInline]

    def get_customer(self, obj):
        if obj.customer_name:
            return obj.customer_name
        if obj.student:
            return f"{obj.student.first_name} {obj.student.last_name}"
        return "Walk-in Customer"
    get_customer.short_description = "Customer"

    def get_terminal(self, obj):
        return str(obj.terminal) if obj.terminal else "—"
    get_terminal.short_description = "Terminal"

    def get_staff(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "—"
    get_staff.short_description = "Staff"
