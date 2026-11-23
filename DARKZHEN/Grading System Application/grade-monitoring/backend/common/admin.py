from django.contrib import admin

from .models import SystemConfig


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ("school_name", "short_name", "default_school_year", "updated_by", "updated_at")
    readonly_fields = ("school_name", "short_name", "logo", "default_school_year", "updated_by", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
