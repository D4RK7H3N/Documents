from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'sale',
        'amount',
        'payment_method',
        'reference_number',
        'gcash_number',
        'created_at',  # Correct field name
    ]
    list_filter = [
        'payment_method',
        'created_at',  # Correct field name
    ]
    search_fields = [
        'reference_number',
        'gcash_number',
        'sale__id',
        'sale__customer_name',
        'sale__student__first_name',
        'sale__student__last_name',
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'  # Correct field name
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale',)
        }),
        ('Payment Details', {
            'fields': ('amount', 'payment_method')
        }),
        ('Reference Information', {
            'fields': ('reference_number', 'gcash_number'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer(self, obj):
        """Display customer name in admin"""
        if obj.sale.student:
            return f"{obj.sale.student.first_name} {obj.sale.student.last_name}"
        return obj.sale.customer_name or "Walk-in Customer"
    get_customer.short_description = 'Customer'