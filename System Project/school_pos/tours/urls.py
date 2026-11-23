from django.urls import path
from . import views

app_name = 'tours'

urlpatterns = [
    # Main dashboard
    path('', views.tour_payment_dashboard, name='payment_dashboard'),
    
    # Tour management
    path('list/', views.tour_list, name='tour_list'),
    path('create/', views.create_tour, name='create_tour'),
    path('edit/<int:tour_id>/', views.edit_tour, name='edit_tour'),
    path('delete/<int:tour_id>/', views.delete_tour, name='delete_tour'),
    path('api/companies/', views.get_tour_companies, name='get_tour_companies'),  # Optional AJAX endpoint
    
    # Section views
    path('sections/', views.section_list_view, name='section_list'),
    path('sections/print/', views.print_section_list, name='print_section_list'),
    path('sections/export/', views.export_section_excel, name='export_section_excel'),
    path('sections/summary/', views.section_payment_summary, name='section_payment_summary'),
    
    # Student payment details
    path('enrollment/<int:enrollment_id>/', views.student_payment_detail, name='student_payment_detail'),
    path('enrollment/<int:enrollment_id>/pay/', views.process_tour_payment, name='process_payment'),
    path('payment/<int:payment_id>/receipt/', views.payment_receipt, name='payment_receipt'),
    
    # Enrollment management
    path('enrollment-management/', views.enrollment_management, name='enrollment_management'),
    path('add-student/', views.add_student_to_tour, name='add_student_to_tour'),
    path('bulk-enroll/', views.bulk_enroll_students_ajax, name='bulk_enroll_ajax'),
]