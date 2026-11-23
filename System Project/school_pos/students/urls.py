from django.urls import path
from . import views

# Import student_documents views if the file exists
try:
    from . import student_documents
    DOCS_AVAILABLE = True
except ImportError:
    DOCS_AVAILABLE = False

app_name = 'students'

urlpatterns = [
    # Student management
    path('', views.student_list, name='student_list'),
    path('enroll/', views.enroll_student, name='enroll_student'),
    path('upload/', views.upload_students, name='upload_students'),
    path('update-info/<int:student_id>/', views.update_info, name='update_info'),
    path('update-grade/<int:student_id>/', views.update_grade, name='update_grade'),
    path('sectioning/', views.student_sectioning, name='student_sectioning'),
    path('update-section/', views.update_section, name='update_section'),
    
    # Tuition payments
    path('tuition-payment/<int:student_id>/', views.tuition_payment, name='tuition_payment'),
    path('tuition-payment-search/', views.tuition_payment_search, name='tuition_payment_search'),
    path('tuition-receipt/<int:payment_id>/', views.tuition_receipt, name='tuition_receipt'),
    path('statement/<int:student_id>/', views.student_statement, name='student_statement'),
    
    # Payment management
    path('payment-history/<int:student_id>/', views.payment_history, name='payment_history'),
    path('payment/edit/<int:payment_id>/', views.edit_tuition_payment, name='edit_tuition_payment'),
    path('payment/delete/<int:payment_id>/', views.delete_tuition_payment, name='delete_tuition_payment'),
    path('update-tuition/<int:student_id>/', views.update_tuition_amount, name='update_tuition_amount'),

    path('year-level-management/', views.year_level_management, name='year_level_management'),
    path('auto-promote-students/', views.auto_promote_students, name='auto_promote_students'),
    path('bulk-update-year-level/', views.bulk_update_year_level, name='bulk_update_year_level'),
    path('reset-sections/', views.reset_sections, name='reset_sections'),
    path('bulk-assign-section/', views.bulk_assign_section, name='bulk_assign_section'),
    path('section-stats/', views.get_section_stats, name='get_section_stats'),
    path('auto-assign-sections/', views.auto_assign_sections, name='auto_assign_sections'),

    # Tour enrollments
    path('with-tours/', views.students_with_tours, name='students_with_tours'),
    # pop-up modal for student quick update
    path('update-student-quick/', views.update_student_quick, name='update_student_quick'),
    
    # Sale receipts
    path('sale-receipt/<int:sale_id>/', views.sale_receipt, name='sale_receipt'),
    path('tuition-receipt-modal/<int:payment_id>/', views.tuition_receipt_modal, name='tuition_receipt_modal'),
    
    # Printable sections
    path('printable-sections/', views.printable_sections, name='printable_sections'),
    path('print-section/<str:section_name>/<str:track_strand>/', views.print_single_section, name='print_single_section'),
]

# Only add document URLs if student_documents.py exists
if DOCS_AVAILABLE:
    urlpatterns += [
        path('documents/<int:student_id>/', student_documents.student_documents_list, name='student_documents'),
        path('documents/<int:student_id>/upload/', student_documents.upload_student_document, name='upload_document'),
        path('documents/<int:document_id>/download/', student_documents.download_student_document, name='download_document'),
        path('documents/<int:document_id>/delete/', student_documents.delete_student_document, name='delete_document'),
    ]