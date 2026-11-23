from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from datetime import datetime
import os
from .models import Student, StudentDocument, StudentData


@login_required
def student_documents_list(request, student_id):
    """View all documents for a student"""
    student = get_object_or_404(Student, id=student_id)
    documents = StudentDocument.objects.filter(student=student).order_by('document_type')
    enrollment_data, created = StudentData.objects.get_or_create(student=student)
    
    context = {
        'student': student,
        'documents': documents,
        'enrollment_data': enrollment_data,
        'document_types': StudentDocument.DOCUMENT_TYPE_CHOICES,
    }
    return render(request, 'students/student_documents.html', context)


@login_required
def upload_student_document(request, student_id):
    """Upload a document for a student"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        try:
            document_type = request.POST.get('document_type')
            description = request.POST.get('description', '')
            file = request.FILES.get('file')
            
            if not document_type:
                messages.error(request, '❌ Please select a document type!')
                return redirect('students:student_documents', student_id=student.id)
            
            if not file:
                messages.error(request, '❌ Please select a file to upload!')
                return redirect('students:student_documents', student_id=student.id)
            
            if file.size > 10 * 1024 * 1024:
                messages.error(request, '❌ File size cannot exceed 10MB!')
                return redirect('students:student_documents', student_id=student.id)
            
            existing = StudentDocument.objects.filter(student=student, document_type=document_type).first()
            
            if existing:
                if existing.file:
                    existing.file.delete()
                existing.file = file
                existing.description = description
                existing.save()
                messages.success(request, f'✅ {existing.get_document_type_display()} updated!')
            else:
                document = StudentDocument.objects.create(
                    student=student,
                    document_type=document_type,
                    file=file,
                    description=description
                )
                enrollment_data, _ = StudentData.objects.get_or_create(student=student)
                if document_type == 'PSA':
                    enrollment_data.psa_submitted = True
                elif document_type == 'PHOTO_2x2':
                    enrollment_data.photos_submitted = True
                elif document_type == 'REPORT_CARD_G10':
                    enrollment_data.report_card_submitted = True
                enrollment_data.save()
                messages.success(request, f'✅ {document.get_document_type_display()} uploaded!')
            
            return redirect('students:student_documents', student_id=student.id)
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('students:student_documents', student_id=student.id)
    
    context = {'student': student, 'document_types': StudentDocument.DOCUMENT_TYPE_CHOICES}
    return render(request, 'students/upload_document.html', context)


@login_required
def download_student_document(request, document_id):
    """Download a document"""
    document = get_object_or_404(StudentDocument, id=document_id)
    try:
        file_path = document.file.path
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=f"{document.student.lrn}_{document.get_document_type_display()}{os.path.splitext(file_path)[1]}")
        messages.error(request, '❌ File not found!')
        raise Http404("File not found")
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
        raise Http404(str(e))


@login_required
def delete_student_document(request, document_id):
    """Delete a document"""
    document = get_object_or_404(StudentDocument, id=document_id)
    student_id = document.student.id
    
    if request.method == 'POST':
        try:
            if document.file:
                document.file.delete()
            enrollment_data = StudentData.objects.filter(student=document.student).first()
            if enrollment_data:
                if document.document_type == 'PSA':
                    enrollment_data.psa_submitted = False
                elif document.document_type == 'PHOTO_2x2':
                    enrollment_data.photos_submitted = False
                elif document.document_type == 'REPORT_CARD_G10':
                    enrollment_data.report_card_submitted = False
                enrollment_data.save()
            document.delete()
            messages.success(request, '✅ Document deleted!')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
        return redirect('students:student_documents', student_id=student_id)
    
    context = {'document': document}
    return render(request, 'students/delete_document.html', context)


@login_required
def student_enrollment_data(request, student_id):
    """Edit enrollment data"""
    student = get_object_or_404(Student, id=student_id)
    enrollment_data, _ = StudentData.objects.get_or_create(student=student)
    
    if request.method == 'POST':
        try:
            enrollment_data.emergency_contact_name = request.POST.get('emergency_contact_name', '')
            enrollment_data.emergency_contact_number = request.POST.get('emergency_contact_number', '')
            enrollment_data.emergency_contact_relationship = request.POST.get('emergency_contact_relationship', '')
            enrollment_data.health_concerns = request.POST.get('health_concerns', '')
            enrollment_data.blood_type_choice = request.POST.get('blood_type_choice', '')
            enrollment_data.notes = request.POST.get('notes', '')
            enrollment_data.save()
            messages.success(request, '✅ Enrollment data updated!')
            return redirect('students:student_enrollment_data', student_id=student.id)
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
    
    context = {
        'student': student,
        'enrollment_data': enrollment_data,
        'blood_types': StudentData.BLOOD_TYPE_CHOICES,
    }
    return render(request, 'students/enrollment_data.html', context)