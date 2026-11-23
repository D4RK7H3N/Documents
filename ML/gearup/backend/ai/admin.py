from django.contrib import admin

from .models import ChatLog


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message", "created_at")
    search_fields = ("message", "response", "user__username")
    readonly_fields = ("user", "message", "response", "retrieved_product_ids", "created_at")
