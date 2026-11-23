from django.contrib import admin

from .models import Prediction


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("id", "prediction", "confidence", "model_version", "created_at")
    list_filter = ("prediction", "model_version")
    search_fields = ("input_text",)
    readonly_fields = ("input_text", "prediction", "confidence", "model_version", "created_at")
