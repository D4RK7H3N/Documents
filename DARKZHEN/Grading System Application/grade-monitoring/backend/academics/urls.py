from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("admin/students", views.StudentViewSet, basename="admin-students")
router.register("admin/sections", views.SectionViewSet, basename="admin-sections")
router.register("admin/subjects", views.SubjectViewSet, basename="admin-subjects")
router.register("admin/assignments", views.AssignmentViewSet, basename="admin-assignments")

urlpatterns = [
    path("teacher/classes/", views.TeacherClassesView.as_view(), name="teacher-classes"),
    path("admin/students/import/", views.StudentImportView.as_view(), name="admin-students-import"),
    path("teachers/", views.TeacherPickerView.as_view(), name="teacher-picker"),
    path("admin/teachers/", views.TeacherConfigView.as_view(), name="admin-teachers"),
    path("admin/users/", views.UserListView.as_view(), name="admin-users"),
    path("", include(router.urls)),
]
