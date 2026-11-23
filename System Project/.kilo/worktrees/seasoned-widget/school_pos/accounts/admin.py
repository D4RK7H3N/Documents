from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'delete_button')

    def delete_button(self, obj):
        url = reverse('admin:auth_user_delete', args=[obj.pk])
        return format_html(
            '<a href="{}" style="color: #e74c3c;" title="Delete this user">'
            '<i class="fas fa-trash"></i></a>',
            url
        )
    delete_button.short_description = 'Delete'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
