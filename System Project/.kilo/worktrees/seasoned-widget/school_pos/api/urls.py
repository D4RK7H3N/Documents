from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginViewSet,
    StudentViewSet,
    StudentDocumentViewSet,
    DormBuildingViewSet,
    DormRoomViewSet,
    DormAssignmentViewSet,
    DormPaymentViewSet,
    ProductViewSet,
    SaleViewSet,
    TuitionPaymentViewSet,
    PaymentViewSet,
    StudentChargeViewSet,
    AssessmentTypeViewSet,
    StudentAssessmentViewSet,
    AssessmentPaymentViewSet,
    EducationalTourViewSet,
    TourEnrollmentViewSet,
    TourPaymentViewSet,
    GraduationEventViewSet,
    StudentGraduationViewSet,
    GraduationPaymentViewSet,
    RevenueViewSet,
)
from tracks.views import TrackViewSet, StrandViewSet, CourseViewSet, SectionViewSet
from dropouts.views import DropoutViewSet

router = DefaultRouter()
router.register(r"auth", LoginViewSet, basename="auth")
router.register(r"students", StudentViewSet, basename="students")
router.register(r"documents", StudentDocumentViewSet, basename="documents")
router.register(r"dorm/buildings", DormBuildingViewSet, basename="dorm-buildings")
router.register(r"dorm/rooms", DormRoomViewSet, basename="dorm-rooms")
router.register(r"dorm/assignments", DormAssignmentViewSet, basename="dorm-assignments")
router.register(r"dorm/payments", DormPaymentViewSet, basename="dorm-payments")
router.register(r"products", ProductViewSet, basename="products")
router.register(r"sales", SaleViewSet, basename="sales")
router.register(r"payments", PaymentViewSet, basename="payments")
router.register(r"charges", StudentChargeViewSet, basename="charges")
router.register(r"tuition-payments", TuitionPaymentViewSet, basename="tuition-payments")

# Assessment endpoints
router.register(r"assessment-types", AssessmentTypeViewSet, basename="assessment-types")
router.register(
    r"student-assessments", StudentAssessmentViewSet, basename="student-assessments"
)
router.register(
    r"assessment-payments", AssessmentPaymentViewSet, basename="assessment-payments"
)

# Tour endpoints
router.register(r"tours", EducationalTourViewSet, basename="tours")
router.register(r"tour-enrollments", TourEnrollmentViewSet, basename="tour-enrollments")
router.register(r"tour-payments", TourPaymentViewSet, basename="tour-payments")

# Graduation endpoints
router.register(
    r"graduation-events", GraduationEventViewSet, basename="graduation-events"
)
router.register(
    r"graduation-enrollments",
    StudentGraduationViewSet,
    basename="graduation-enrollments",
)
router.register(
    r"graduation-payments", GraduationPaymentViewSet, basename="graduation-payments"
)

# Revenue endpoints
router.register(r"revenue", RevenueViewSet, basename="revenue")

# Track/Strand endpoints
router.register(r"tracks", TrackViewSet, basename="tracks")
router.register(r"strands", StrandViewSet, basename="strands")
router.register(r"courses", CourseViewSet, basename="courses")
router.register(r"sections", SectionViewSet, basename="sections")

# Dropout endpoints
router.register(r"dropouts", DropoutViewSet, basename="dropouts")

from .updates_view import serve_update_file
from .health import health_check

urlpatterns = [
    path("", include(router.urls)),
    path("health/", health_check, name="health-check"),
    path("school-config/", include("school_config.urls")),
    # App updates endpoint
    path("updates/<str:filename>", serve_update_file, name="serve-update-file"),
]