from django.contrib import admin

from .models import ClassAssignment, Section, StudentProfile, Subject


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "school_year")
    list_filter = ("school_year",)
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "subject_type")
    list_filter = ("subject_type",)
    search_fields = ("name",)


@admin.register(ClassAssignment)
class ClassAssignmentAdmin(admin.ModelAdmin):
    list_display = ("subject", "section", "teacher", "school_year")
    list_filter = ("school_year", "section", "subject")
    search_fields = ("subject__name", "section__name", "teacher__username")
    autocomplete_fields = ["subject", "section", "teacher"]


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("lrn", "full_name", "section", "user")
    list_filter = ("section",)
    search_fields = ("lrn", "full_name")
    autocomplete_fields = ["user", "section"]
