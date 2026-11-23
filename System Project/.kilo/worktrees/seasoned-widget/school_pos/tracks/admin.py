from django.contrib import admin
from .models import Track, Strand, Course


class StrandInline(admin.TabularInline):
    """Inline for managing strands within a track"""
    model = Strand
    extra = 1
    fields = ['name', 'code', 'description', 'is_active']


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'level_type', 'strand_count', 'is_active', 'created_at']
    list_filter = ['level_type', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    inlines = [StrandInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'description')
        }),
        ('Settings', {
            'fields': ('level_type', 'is_active')
        }),
    )

    def strand_count(self, obj):
        return obj.strands.count()
    strand_count.short_description = 'Strands'


@admin.register(Strand)
class StrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'track', 'is_active', 'created_at']
    list_filter = ['track', 'is_active']
    search_fields = ['name', 'code', 'description', 'track__name']
    ordering = ['track', 'name']
    autocomplete_fields = ['track']

    fieldsets = (
        (None, {
            'fields': ('track', 'name', 'code', 'description')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'level_type', 'duration_years', 'is_active', 'created_at']
    list_filter = ['level_type', 'is_active', 'duration_years']
    search_fields = ['name', 'code', 'abbreviation', 'description']
    ordering = ['name']

    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'abbreviation', 'description')
        }),
        ('Academic Details', {
            'fields': ('level_type', 'duration_years')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )
