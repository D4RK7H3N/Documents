from django.contrib import admin
from .models import EducationalTour, TourEnrollment, TourPayment

@admin.register(EducationalTour)
class EducationalTourAdmin(admin.ModelAdmin):
    list_display = ['name', 'destination', 'tour_date', 'total_cost', 'status', 'get_participants']
    list_filter = ['status', 'tour_date']
    search_fields = ['name', 'destination']
    date_hierarchy = 'tour_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'destination', 'description', 'status')
        }),
        ('Dates', {
            'fields': ('tour_date', 'return_date')
        }),
        ('Costs', {
            'fields': ('total_cost', 'transportation_fee', 'accommodation_fee', 
                      'food_allowance', 'entrance_fees', 'other_fees')
        }),
        ('Capacity', {
            'fields': ('max_participants',)
        }),
    )
    
    def get_participants(self, obj):
        return obj.get_total_participants()
    get_participants.short_description = 'Participants'


@admin.register(TourEnrollment)
class TourEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'tour', 'enrollment_date', 'total_fee', 'amount_paid', 'balance', 'status']
    list_filter = ['status', 'tour', 'enrollment_date']
    search_fields = ['student__first_name', 'student__last_name', 'student__lrn', 'tour__name']
    date_hierarchy = 'enrollment_date'
    
    readonly_fields = ['balance', 'created_at', 'updated_at']


@admin.register(TourPayment)
class TourPaymentAdmin(admin.ModelAdmin):
    list_display = ['student', 'tour', 'amount', 'payment_date', 'method', 'received_by']
    list_filter = ['method', 'payment_date', 'tour']
    search_fields = ['student__first_name', 'student__last_name', 'reference_number']
    date_hierarchy = 'payment_date'
    
    readonly_fields = ['created_at']