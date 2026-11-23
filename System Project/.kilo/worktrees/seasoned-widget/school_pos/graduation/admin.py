from django.contrib import admin
from .models import GraduationEvent, StudentGraduation, GraduationPayment

@admin.register(GraduationEvent)
class GraduationEventAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'event_date', 'graduation_package_fee', 'total_fee_per_student', 'status',
        'get_participants', 'get_total_paid', 'is_registration_open'
    ]
    list_filter = ['status', 'event_date']
    search_fields = ['name', 'venue']
    date_hierarchy = 'event_date'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'status')
        }),
        ('Dates', {
            'fields': ('event_date', 'registration_deadline')
        }),
        ('Fee Structure', {
            'fields': (
                'graduation_package_fee', 'total_fee_per_student'
            )
        }),
        ('Event Details', {
            'fields': ('venue', 'time', 'max_participants')
        }),
    )

    readonly_fields = ['total_fee_per_student', 'created_at', 'updated_at']

    def get_participants(self, obj):
        return obj.get_total_participants()
    get_participants.short_description = 'Registered'

    def get_total_paid(self, obj):
        return f"₱{obj.get_total_paid():,.2f}"
    get_total_paid.short_description = 'Total Paid'

    def is_registration_open(self, obj):
        return obj.is_registration_open()
    is_registration_open.short_description = 'Registration Open'
    is_registration_open.boolean = True


@admin.register(StudentGraduation)
class StudentGraduationAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'graduation_event', 'graduation_level',
        'section', 'registration_date', 'total_fee',
        'amount_paid', 'balance', 'status'
    ]
    list_filter = ['status', 'graduation_level', 'graduation_event', 'registration_date']
    search_fields = [
        'student__first_name', 'student__last_name',
        'student__lrn', 'section'
    ]
    date_hierarchy = 'registration_date'

    readonly_fields = ['balance', 'created_at', 'updated_at']


@admin.register(GraduationPayment)
class GraduationPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'graduation_event', 'amount',
        'payment_date', 'method', 'received_by'
    ]
    list_filter = ['method', 'payment_date', 'graduation_event']
    search_fields = [
        'student__first_name', 'student__last_name',
        'reference_number', 'gcash_number'
    ]
    date_hierarchy = 'payment_date'

    readonly_fields = ['created_at', 'updated_at']