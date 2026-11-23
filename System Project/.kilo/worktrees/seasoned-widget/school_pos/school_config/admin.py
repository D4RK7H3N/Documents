from django.contrib import admin
from django.utils.html import format_html
from .models import SchoolConfiguration


@admin.register(SchoolConfiguration)
class SchoolConfigurationAdmin(admin.ModelAdmin):
    list_display = ['school_name', 'school_short_name', 'city', 'logo_thumbnail', 'updated_at']
    readonly_fields = ['created_at', 'updated_at', 'logo_preview', 'header_logo_preview']

    fieldsets = (
        ('School Information', {
            'fields': ('school_name', 'school_short_name', 'tagline', 'current_academic_year', 'student_id_prefix')
        }),
        ('Contact Information', {
            'fields': ('address_line1', 'address_line2', 'city', 'province', 'zip_code', 'country', 'phone_number', 'mobile_number', 'email', 'website')
        }),
        ('Branding', {
            'fields': ('logo', 'logo_preview', 'header_logo', 'header_logo_preview'),
            'description': 'Upload logo here OR via the School Config page in the frontend app — both sync automatically.'
        }),
        ('Receipt Configuration', {
            'fields': ('receipt_header_text', 'receipt_footer_text')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def logo_thumbnail(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:30px; width:30px; border-radius:50%; object-fit:cover;" />',
                obj.logo.url
            )
        return '—'
    logo_thumbnail.short_description = 'Logo'

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height:120px; border-radius:8px; margin-top:8px;" />',
                obj.logo.url
            )
        return 'No logo uploaded'
    logo_preview.short_description = 'Logo Preview'

    def header_logo_preview(self, obj):
        if obj.header_logo:
            return format_html(
                '<img src="{}" style="max-height:60px; margin-top:8px;" />',
                obj.header_logo.url
            )
        return 'No header logo uploaded'
    header_logo_preview.short_description = 'Header Logo Preview'

    def has_add_permission(self, request):
        return not SchoolConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False