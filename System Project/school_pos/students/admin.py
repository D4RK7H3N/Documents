from django.contrib import admin
from .models import Student

# Try to import new models, but don't fail if they don't exist yet
try:
    from .models import StudentDocument, StudentData

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False


# Register existing Student admin (keep your existing one)
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "lrn",
        "last_name",
        "first_name",
        "gender",
        "contact_number",
        "level_type",
        "enrollment_status",
        "student_type",
        "status",
        "date_of_enrollment",
    )
    list_filter = (
        "gender",
        "level_type",
        "enrollment_status",
        "student_type",
        "status",
        "date_of_enrollment",
    )
    search_fields = ("lrn", "first_name", "last_name", "email", "contact_number")
    readonly_fields = ("date_of_enrollment",)


# Only register new models if they exist
if MODELS_AVAILABLE:

    @admin.register(StudentDocument)
    class StudentDocumentAdmin(admin.ModelAdmin):
        list_display = ("student", "document_type", "is_verified", "uploaded_at")
        list_filter = ("document_type", "is_verified", "uploaded_at")
        search_fields = ("student__lrn", "student__first_name", "student__last_name")
        readonly_fields = ("uploaded_at", "updated_at", "verified_by", "verified_at")

    @admin.register(StudentData)
    class StudentDataAdmin(admin.ModelAdmin):
        list_display = ("student", "enrollment_date", "is_complete")
        list_filter = ("is_complete", "enrollment_date")
        search_fields = ("student__lrn", "student__first_name", "student__last_name")
        readonly_fields = ("enrollment_date", "updated_at")
