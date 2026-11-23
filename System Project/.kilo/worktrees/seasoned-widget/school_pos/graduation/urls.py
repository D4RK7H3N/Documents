from django.urls import path
from . import views

app_name = 'graduation'

urlpatterns = [
    path('', views.graduation_dashboard, name='dashboard'),
    path('create/', views.create_event, name='create_event'),
    path('<int:event_id>/', views.graduation_event_detail, name='event_detail'),
    path('<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('<int:event_id>/register/', views.register_student, name='register_student'),
    path('student/<int:student_graduation_id>/', views.student_detail, name='student_detail'),
    path('student/<int:student_graduation_id>/payment/', views.payment, name='payment'),
    path('student/<int:student_graduation_id>/delete/', views.delete_registration, name='delete_registration'),
    path('students-with-balance/', views.students_with_balance, name='students_with_balance'),
    path('summary-report/', views.graduation_summary_report, name='summary_report'),
]