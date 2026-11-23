from django.contrib import admin

from .models import (
    Assessment,
    GeneralAverage,
    GradingConfig,
    QuarterGrade,
    QuarterLock,
    Score,
    SemesterGrade,
)


@admin.register(GradingConfig)
class GradingConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_by", "updated_at")


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "class_assignment", "component", "quarter", "highest_possible_score")
    list_filter = ("quarter", "component")
    search_fields = ("title",)
    autocomplete_fields = ["class_assignment"]


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("assessment", "student", "raw_score", "updated_at")
    list_filter = ("assessment__quarter",)
    search_fields = ("student__lrn", "student__full_name")
    autocomplete_fields = ["assessment", "student"]


@admin.register(QuarterGrade)
class QuarterGradeAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "quarter", "grade", "initial_grade", "computed_at")
    list_filter = ("quarter", "subject")
    search_fields = ("student__lrn", "student__full_name")
    autocomplete_fields = ["student", "subject"]


@admin.register(SemesterGrade)
class SemesterGradeAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "semester", "final", "computed_at")
    list_filter = ("semester",)
    search_fields = ("student__lrn",)
    autocomplete_fields = ["student", "subject"]


@admin.register(GeneralAverage)
class GeneralAverageAdmin(admin.ModelAdmin):
    list_display = ("student", "semester", "average", "computed_at")
    list_filter = ("semester",)
    search_fields = ("student__lrn",)
    autocomplete_fields = ["student"]


@admin.register(QuarterLock)
class QuarterLockAdmin(admin.ModelAdmin):
    list_display = ("class_assignment", "quarter", "locked_by", "locked_at")
    list_filter = ("quarter",)
    autocomplete_fields = ["class_assignment"]
