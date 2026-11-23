from django.urls import path

from . import views

urlpatterns = [
    path("classes/<int:class_id>/assessments/", views.ClassAssessmentsView.as_view(), name="class-assessments"),
    path("assessments/<int:assessment_id>/", views.AssessmentDetailView.as_view(), name="assessment-detail"),
    path("assessments/<int:assessment_id>/scores/", views.AssessmentScoresView.as_view(), name="assessment-scores"),
    path("students/<int:student_id>/record/", views.StudentRecordView.as_view(), name="student-record"),
    path("classes/<int:class_id>/grades/", views.ClassGradesView.as_view(), name="class-grades"),
    path("sections/<int:section_id>/report/", views.SectionReportView.as_view(), name="section-report"),
    path("classes/<int:class_id>/semester-report/", views.ClassSemesterReportView.as_view(), name="class-semester-report"),
    path("classes/<int:class_id>/submissions/", views.SubmissionCreateView.as_view(), name="submission-create"),
    path("submissions/", views.SubmissionView.as_view(), name="submissions"),
    path("submissions/<int:submission_id>/<str:decision>/", views.SubmissionDecisionView.as_view(), name="submission-decision"),
    path("me/grades/", views.MyGradesView.as_view(), name="my-grades"),
    path("admin/grading-config/", views.GradingConfigView.as_view(), name="grading-config"),
    path(
        "admin/classes/<int:class_id>/quarters/<int:quarter>/lock/",
        views.QuarterLockView.as_view(),
        name="quarter-lock",
    ),
]
