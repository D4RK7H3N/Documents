# assessment/urls.py

from django.urls import path
from . import views

app_name = 'assessment'

urlpatterns = [
    # Main dashboard
    path('', views.assessment_dashboard, name='dashboard'),
    
    # Assessment details and payments
    path('<int:assessment_id>/', views.assessment_detail, name='detail'),
    path('<int:assessment_id>/payment/', views.process_assessment_payment, name='process_payment'),
    path('receipt/<int:payment_id>/', views.payment_receipt, name='payment_receipt'),
    path('statement/<int:assessment_id>/', views.assessment_statement, name='statement'),
    
    # Student-specific views
    path('student/<int:student_id>/', views.student_assessments, name='student_assessments'),
    # Assessment type management
    path('admin/types/', views.manage_assessment_types, name='manage_types'),
    path('admin/types/create/', views.create_assessment_type, name='create_type'),
    
    # Assignment
    path('admin/assign/<int:student_id>/', views.assign_assessment, name='assign_assessment'),
    path('admin/batch-assign/', views.batch_assign_assessment, name='batch_assign'),
]