from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "role", "is_active", "must_change_password", "is_staff")
    list_filter = ("role", "is_active", "must_change_password")
    fieldsets = UserAdmin.fieldsets + (
        ("Application", {"fields": ("role", "must_change_password", "failed_login_attempts", "locked_until")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (("Application", {"fields": ("role",)}),)
    search_fields = ("username",)
    readonly_fields = ("failed_login_attempts", "locked_until")
