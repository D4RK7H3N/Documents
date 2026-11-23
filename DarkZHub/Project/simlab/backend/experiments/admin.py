from django.contrib import admin

from .models import Experiment, SweepExperiment


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ("id", "engine", "status", "engine_version", "created_at", "finished_at")
    list_filter = ("status", "engine")
    readonly_fields = ("id", "result", "error")


@admin.register(SweepExperiment)
class SweepExperimentAdmin(admin.ModelAdmin):
    list_display = ("id", "engine", "status", "created_at")
    list_filter = ("status", "engine")
    readonly_fields = ("id", "results")
