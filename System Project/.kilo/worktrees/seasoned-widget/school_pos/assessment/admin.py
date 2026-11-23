from django.contrib import admin
from .models import AssessmentType, StudentAssessment, AssessmentPayment, AssessmentBatch


@admin.register(AssessmentType)
class AssessmentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'amount', 'applicable_to', 'is_active', 'is_required']
    list_filter = ['category', 'applicable_to', 'is_active', 'is_required']
    search_fields = ['name', 'code', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'category', 'description')
        }),
        ('Financial', {
            'fields': ('amount',)
        }),
        ('Applicability', {
            'fields': ('applicable_to', 'applicable_tracks', 'is_required')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(StudentAssessment)
class StudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'assessment_type', 'total_fee', 'amount_paid', 'balance', 'status', 'date_assessed']
    list_filter = ['status', 'assessment_type', 'date_assessed']
    search_fields = [
        'student__first_name', 
        'student__last_name', 
        'student__lrn',
        'assessment_type__name'
    ]
    date_hierarchy = 'date_assessed'
    
    readonly_fields = ['balance', 'created_at', 'updated_at']


@admin.register(AssessmentPayment)
class AssessmentPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 
        'assessment_type', 
        'amount', 
        'payment_date', 
        'payment_method', 
        'received_by'
    ]
    list_filter = ['payment_method', 'payment_date', 'assessment_type']
    search_fields = [
        'student__first_name', 
        'student__last_name', 
        'reference_number',
        'gcash_number'
    ]
    date_hierarchy = 'payment_date'
    
    readonly_fields = ['created_at']


@admin.register(AssessmentBatch)
class AssessmentBatchAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'assessment_type', 
        'level_type', 
        'students_count', 
        'total_amount', 
        'created_at'
    ]
    list_filter = ['level_type', 'assessment_type', 'created_at']
    search_fields = ['name', 'track_strand', 'section']
    date_hierarchy = 'created_at'
    
    readonly_fields = ['students_count', 'total_amount', 'created_at']