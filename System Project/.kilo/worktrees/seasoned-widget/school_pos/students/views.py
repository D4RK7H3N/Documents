from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Q, Sum, Count, Exists, OuterRef
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import Student
from django.http import JsonResponse
from tuition.models import TuitionPayment
from .forms import StudentEnrollmentForm
from sales.models import Sale, SaleItem
from products.models import Product
from tours.models import TourEnrollment
import csv
from io import TextIOWrapper
from decimal import Decimal
import openpyxl
from openpyxl import load_workbook
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
import json


def get_tuition_fee(student):
    """
    Tuition fee for a student, taken from their own custom_tuition_fee.

    There is no fee lookup table - tuition is set per student at enrollment
    (or via the Tuition column on bulk upload). Returns 0 when unset rather
    than guessing an amount.
    """
    if hasattr(student, 'custom_tuition_fee') and student.custom_tuition_fee:
        return float(student.custom_tuition_fee)
    return 0


def get_tuition_breakdown(student):
    """
    Get tuition breakdown based on level type.

    SHS: First Sem (first_quarter, second_quarter), Second Sem (third_quarter, fourth_quarter)
    BUN: First Sem, Second Sem only
    """
    tuition_fee = get_tuition_fee(student)

    if student.level_type == "SHS":
        half = tuition_fee / 2
        quarter = tuition_fee / 4
        return {
            "first_sem": half,
            "first_quarter": quarter,
            "second_quarter": quarter,
            "second_sem": half,
            "third_quarter": quarter,
            "fourth_quarter": quarter,
        }
    elif student.level_type == "BUN":
        half = tuition_fee / 2
        return {
            "first_sem": half,
            "second_sem": half,
        }
    return None


def recalculate_student_balance(student):
    """
    Recalculate student's tuition balance from scratch
    This ensures accuracy even if manual edits caused discrepancies
    """
    # Determine expected tuition based on level and enrollment status
    expected_tuition = get_tuition_fee(student)

    # Calculate total paid from all payment records
    total_paid = TuitionPayment.objects.filter(
        student=student
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate new balance
    new_balance = expected_tuition - total_paid

    # Update student's balance
    student.tuition_balance = new_balance
    student.save()

    return new_balance


@login_required
def tuition_payment(request, student_id):
    """Handle tuition payment for a specific student with AJAX support."""
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            amount = Decimal(request.POST.get("amount", 0))
        except Exception:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid payment amount.'
                }, status=400)
            messages.error(request, "Invalid payment amount.")
            return redirect("students:tuition_payment", student_id=student.id)

        method = request.POST.get("payment_method", "Cash")
        reference_no = request.POST.get("reference_no", "")
        gcash_number = request.POST.get("gcash_number", "") 
        remarks = request.POST.get("remarks", "")

        if amount <= 0:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': 'Payment amount must be greater than zero.'
                }, status=400)
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect("students:tuition_payment", student_id=student.id)

        with transaction.atomic():
            student = Student.objects.select_for_update().get(id=student_id)
            # Deduct from balance
            student.tuition_balance -= amount
            student.save()

            # Save the payment record
            payment = TuitionPayment.objects.create(
                student=student,
                amount=amount,
                method=method,
                date=timezone.localtime(timezone.now()),
                reference_no=reference_no,
                gcash_number=gcash_number,
                remarks=remarks,
            )

        # If AJAX request, return receipt HTML for modal
        if is_ajax:
            try:
                # Refresh student to get latest balance
                student.refresh_from_db()
                
                # Calculate total paid from all payments
                total_paid = TuitionPayment.objects.filter(
                    student=student
                ).aggregate(Sum("amount"))["amount__sum"] or 0
                
                # Get current balance from database
                current_balance = student.tuition_balance
                
                # Calculate tuition fee based on level type and enrollment status
                tuition_fee = get_tuition_fee(student)
                breakdown = get_tuition_breakdown(student)
                
                # Render receipt HTML
                receipt_html = render_to_string('students/receipt_modal_content.html', {
                    'payment': payment,
                    'student': student,
                    'tuition_fee': tuition_fee,  # Use correct tuition fee
                    'total_paid': float(total_paid),
                    'balance': float(current_balance),
                    'breakdown': breakdown,
                })
                
                return JsonResponse({
                    'success': True,
                    'receipt_html': receipt_html,
                    'new_balance': float(current_balance)
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error generating receipt: {str(e)}'
                }, status=500)

        # Regular form submission (non-AJAX)
        messages.success(request, f"₱{amount:.2f} payment recorded for {student.first_name}.")
        return redirect("students:tuition_receipt", payment_id=payment.id)

    return render(request, "students/tuition_payment_form.html", {"student": student})

    
@login_required
def tuition_receipt(request, payment_id):
    """Printable tuition receipt with remaining balance"""
    payment = get_object_or_404(TuitionPayment, id=payment_id)
    student = payment.student

    # Calculate tuition fee based on level type and enrollment status
    tuition_fee = get_tuition_fee(student)
    breakdown = get_tuition_breakdown(student)

    # Calculate total paid
    total_paid = TuitionPayment.objects.filter(student=student).aggregate(Sum("amount"))["amount__sum"] or 0
    balance = tuition_fee - total_paid

    return render(
        request,
        "students/tuition_receipt.html",
        {
            "payment": payment,
            "student": student,
            "tuition_fee": tuition_fee,
            "total_paid": total_paid,
            "balance": balance,
            "breakdown": breakdown,
        },
    )


@login_required
def sale_receipt(request, sale_id):
    """Printable POS sale receipt"""
    sale = get_object_or_404(Sale, id=sale_id)
    items = sale.items.all()
    
    # Get customer name
    if sale.student:
        customer = f"{sale.student.first_name} {sale.student.last_name}"
    elif sale.customer_name:
        customer = sale.customer_name
    else:
        customer = "Walk-in Customer"

    return render(
        request,
        "students/sale_receipt.html",
        {
            "sale": sale,
            "items": items,
            "customer": customer,
        },
    )


@login_required
def enroll_student(request):
    if request.method == "POST":
        form = StudentEnrollmentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save(commit=False)

            # Auto-set tuition balance based on level type and enrollment status
            enrollment_status = student.enrollment_status
            level_type = student.level_type
            # Check if tuition was manually set (user provided a value)
            manual_tuition = request.POST.get("tuition_balance", "").strip()

            # Determine tuition based on enrollment status
            if enrollment_status == "New":
                # New students: NO tuition by default, only if manually set
                if manual_tuition and manual_tuition != "0":
                    try:
                        student.tuition_balance = float(manual_tuition)
                    except (ValueError, TypeError):
                        student.tuition_balance = 0
                else:
                    student.tuition_balance = 0

            # Continuing / ALS Graduate / Transferee: no fee lookup table, so
            # tuition comes only from an explicitly entered amount. Without one
            # the student starts at 0 and the fee is set on their record later.
            if manual_tuition and manual_tuition != "0":
                try:
                    student.tuition_balance = float(manual_tuition)
                except (ValueError, TypeError):
                    student.tuition_balance = 0
            else:
                student.tuition_balance = 0

            student.save()
            messages.success(request, "Student enrolled successfully!")
            return redirect("students:student_list")
    else:
        form = StudentEnrollmentForm()

    return render(request, "students/enroll.html", {"form": form})


@login_required
def student_list(request):
    query = request.GET.get("q", "")
    level_filter = request.GET.get("level_type", "")
    section_filter = request.GET.get("section", "")
    track_filter = request.GET.get("track_strand", "")
    status_filter = request.GET.get("status", "")
    sort_by = request.GET.get("sort", "name")
    
    # Annotate with tour count
    students = Student.objects.annotate(
        tour_count=Count('tour_enrollments')
    )

    # Search filter
    if query:
        students = students.filter(
            Q(lrn__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(contact_number__icontains=query) |
            Q(email__icontains=query)
        )
    
    # Level type filter
    if level_filter:
        students = students.filter(level_type=level_filter)
    
    # Track/Strand filter
    if track_filter:
        students = students.filter(track_strand=track_filter)
    
    # Section filter
    if section_filter:
        students = students.filter(section=section_filter)
    
    # Status filter
    if status_filter:
        students = students.filter(enrollment_status=status_filter)

    # Sorting
    if sort_by == "name":
        students = students.order_by('last_name', 'first_name')
    elif sort_by == "lrn":
        students = students.order_by('lrn')
    elif sort_by == "section":
        students = students.order_by('section', 'last_name', 'first_name')
    elif sort_by == "track":
        students = students.order_by('track_strand', 'section', 'last_name')
    elif sort_by == "balance":
        students = students.order_by('-tuition_balance', 'last_name')
    else:
        students = students.order_by('last_name', 'first_name')

    # Get all unique values for filter dropdowns
    sections = Student.objects.exclude(
        section__isnull=True
    ).exclude(
        section=''
    ).values_list('section', flat=True).distinct().order_by('section')
    
    tracks = Student.objects.exclude(
        track_strand__isnull=True
    ).exclude(
        track_strand=''
    ).values_list('track_strand', flat=True).distinct().order_by('track_strand')

    # Get available tours for quick enrollment
    from tours.models import EducationalTour
    available_tours = EducationalTour.objects.filter(
        status__in=['Planned', 'Ongoing']
    ).order_by('tour_date')[:5]

    # Delete student functionality
    if request.method == "POST" and "delete_student" in request.POST:
        student_id = request.POST.get("student_id")
        student = get_object_or_404(Student, id=student_id)
        student_name = f"{student.first_name} {student.last_name}"
        student.delete()
        messages.success(request, f"Student {student_name} was deleted.")
        return redirect("students:student_list")

    context = {
        "students": students,
        "query": query,
        "level_filter": level_filter,
        "section_filter": section_filter,
        "track_filter": track_filter,
        "status_filter": status_filter,
        "sort_by": sort_by,
        "sections": sections,
        "tracks": tracks,
        "total_count": students.count(),
        "available_tours": available_tours,
    }

    return render(request, "students/student_list.html", context)


@login_required
def update_info(request, student_id):
    """Quick update for track/strand and section"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == "POST":
        student.track_strand = request.POST.get("track_strand", "")
        student.section = request.POST.get("section", "")
        student.save()
        
        messages.success(request, f"Updated info for {student.first_name} {student.last_name}")
        return redirect("students:student_list")
    
    return render(request, "students/update_info.html", {"student": student})


@login_required
def edit_tuition_payment(request, payment_id):
    """Edit an existing tuition payment"""
    payment = get_object_or_404(TuitionPayment, id=payment_id)
    student = payment.student
    old_amount = payment.amount
    
    if request.method == "POST":
        try:
            new_amount = Decimal(request.POST.get("amount", 0))
        except Exception:
            messages.error(request, "Invalid payment amount.")
            return redirect("students:edit_tuition_payment", payment_id=payment_id)
        
        method = request.POST.get("payment_method", "Cash")
        reference_no = request.POST.get("reference_no", "")
        gcash_number = request.POST.get("gcash_number", "")
        remarks = request.POST.get("remarks", "")
        
        if new_amount <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect("students:edit_tuition_payment", payment_id=payment_id)
        
        with transaction.atomic():
            student = Student.objects.select_for_update().get(id=student.id)
            # Update payment record FIRST
            payment.amount = new_amount
            payment.method = method
            payment.reference_no = reference_no
            payment.gcash_number = gcash_number
            payment.remarks = remarks
            payment.save()

            # Then recalculate balance from ALL payments
            new_balance = recalculate_student_balance(student)
        
        messages.success(request, f"Payment updated! New balance: ₱{new_balance:.2f}")
        return redirect("students:student_statement", student_id=student.id)
    
    return render(request, "students/edit_tuition_payment.html", {
        "payment": payment,
        "student": student
    })


@login_required
def delete_tuition_payment(request, payment_id):
    """Delete a tuition payment and restore the balance"""
    payment = get_object_or_404(TuitionPayment, id=payment_id)
    student = payment.student
    amount = payment.amount
    
    if request.method == "POST":
        with transaction.atomic():
            student = Student.objects.select_for_update().get(id=student.id)
            # Delete the payment FIRST
            payment.delete()

            # Then recalculate balance from remaining payments
            new_balance = recalculate_student_balance(student)
        
        messages.success(request, f"Payment of ₱{amount:.2f} deleted. New balance: ₱{new_balance:.2f}")
        return redirect("students:student_statement", student_id=student.id)
    
    return render(request, "students/confirm_delete_payment.html", {
        "payment": payment,
        "student": student
    })

@login_required
def upload_students(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        
        # Check file extension
        if not file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, "Please upload an Excel file (.xlsx or .xls)")
            return render(request, "students/upload.html")

        try:
            # Load the workbook
            if file.name.endswith('.xlsx'):
                workbook = load_workbook(file)
            else:
                messages.error(request, "Only .xlsx files are supported. Please convert .xls to .xlsx")
                return render(request, "students/upload.html")
            
            # Get the active sheet
            sheet = workbook.active
            
            # Get headers from first row
            headers = []
            for cell in sheet[1]:
                if cell.value:
                    headers.append(str(cell.value).strip().lower())
            
            if not headers:
                messages.error(request, "No headers found in the first row of the Excel file")
                return render(request, "students/upload.html")
            
            count = 0
            errors = []
            
            # Process each row starting from row 2 (skip header)
            for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
                try:
                    # Create a dictionary of column values
                    row_data = {}
                    for idx, header in enumerate(headers):
                        if idx < len(row):
                            cell_value = row[idx].value
                            row_data[header] = cell_value if cell_value is not None else ""
                    
                    # Extract required fields
                    lrn = str(row_data.get('lrn', '')).strip()
                    first_name = str(row_data.get('firstname', '')).strip()
                    last_name = str(row_data.get('lastname', '')).strip()
                    middle_name = str(row_data.get('middle', '')).strip()
                    grade_level = str(row_data.get('gradelevel', '')).strip()
                    level_type = str(row_data.get('leveltype', '')).strip().upper()
                    enrollment_status = str(row_data.get('status', 'New')).strip()
                    tuition = str(row_data.get('tuition', '')).strip()
                    
                    # Validate required fields
                    if not lrn or not last_name or not first_name:
                        errors.append(f"Row {row_num}: Missing required fields (LRN, First Name, or Last Name)")
                        continue
                    
                    # Validate and normalize level type
                    if level_type not in ['SHS', 'COL', 'BUN']:
                        errors.append(f"Row {row_num}: Invalid level type '{level_type}'. Must be SHS, COL, or BUN")
                        continue
                    
                    # Validate and normalize enrollment status
                    valid_statuses = ["New", "Continuing", "Transferee", "ALS Graduate"]
                    if enrollment_status not in valid_statuses:
                        enrollment_status = "New"
                    
                    # Determine tuition balance
                    tuition_balance = 0
                    
                    if tuition:
                        # Custom tuition provided
                        try:
                            tuition_balance = float(tuition)
                        except (ValueError, TypeError):
                            errors.append(f"Row {row_num}: Invalid tuition value '{tuition}'")
                            continue
                    else:
                        # No Tuition column value: leave at 0. Tuition is
                        # assigned manually per student afterwards rather than
                        # inferred from level type.
                        tuition_balance = 0

                    # Determine SHS grade
                    shs_grade = None
                    if level_type == "SHS":
                        if "12" in str(grade_level):
                            shs_grade = "12"
                        else:
                            shs_grade = "11"
                    
                    # Create or update student
                    student, created = Student.objects.update_or_create(
                        lrn=lrn,
                        defaults={
                            "last_name": last_name,
                            "first_name": first_name,
                            "middle_name": middle_name,
                            "current_grade_level": grade_level if grade_level else None,
                            "level_type": level_type,
                            "shs_grade": shs_grade,
                            "enrollment_status": enrollment_status,
                            "tuition_balance": tuition_balance,
                            "is_als_graduate": True if enrollment_status == "ALS Graduate" else False,
                        },
                    )
                    count += 1
                
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            # Display error messages
            if errors:
                for error in errors:
                    messages.warning(request, error)
            
            messages.success(request, f"Successfully imported {count} students from Excel.")
            return redirect("students:student_list")
        
        except Exception as e:
            messages.error(request, f"Error processing Excel file: {str(e)}")
            return render(request, "students/upload.html")

    return render(request, "students/upload.html")


@login_required
def tuition_payment_search(request):
    """Search for students to process tuition payments"""
    students = None
    search_query = request.GET.get('search', '')
    level_filter = request.GET.get('level_type', '')
    
    if search_query or level_filter:
        students = Student.objects.all()
        
        # Search by name or LRN
        if search_query:
            students = students.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(lrn__icontains=search_query)
            )
        
        # Filter by level type
        if level_filter:
            students = students.filter(level_type=level_filter)
        
        students = students.order_by('last_name', 'first_name')
    else:
        students = Student.objects.all().order_by('last_name', 'first_name')
    
    context = {
        'students': students,
        'search_query': search_query,
        'level_filter': level_filter,
    }
    return render(request, 'students/tuition_payment_search.html', context)


@login_required
def student_statement(request, student_id):
    """Generate statement of account for payee students only"""
    student = get_object_or_404(Student, id=student_id)
    
    # Check if student is a payee
    is_non_payee = (
        student.current_grade_level == "Grade 11" or 
        student.tuition_balance == 0
    )
    
    # If student is non-payee, redirect with error
    if is_non_payee:
        messages.error(
            request, 
            f"{student.first_name} {student.last_name} is a non-payee student. Statement of account is not available."
        )
        return redirect('students:student_list')
    
    # Get all payments for this student, ordered by date
    payments = TuitionPayment.objects.filter(
        student=student
    ).order_by('date')

    # Calculate tuition fee based on level type and enrollment status
    tuition_fee = get_tuition_fee(student)
    breakdown = get_tuition_breakdown(student)

    # Calculate total paid
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate current balance
    balance = tuition_fee - total_paid
    
    # Add remaining balance to each payment
    remaining_balance = tuition_fee
    payments_with_balance = []
    for payment in payments:
        remaining_balance -= payment.amount
        payment.remaining_balance = remaining_balance
        payments_with_balance.append(payment)
    
    context = {
        'student': student,
        'payments': payments_with_balance,
        'tuition_fee': tuition_fee,
        'total_paid': total_paid,
        'balance': balance,
        'breakdown': breakdown,
        'current_date': timezone.now(),
        'school_year': '2024-2025',
    }
    
    return render(request, 'students/statement_of_account.html', context)


@login_required
def student_sectioning(request):
    """Student sectioning by level, track, and section"""
    
    # Get filters
    level_filter = request.GET.get('level_type', '')
    track_filter = request.GET.get('track_strand', '')
    section_filter = request.GET.get('section', '')
    
    # Get all students
    students = Student.objects.all()
    
    # Apply filters
    if level_filter:
        students = students.filter(level_type=level_filter)
    if track_filter:
        students = students.filter(track_strand=track_filter)
    if section_filter:
        students = students.filter(section=section_filter)
    
    # Group by section
    sections = {}
    for student in students.order_by('section', 'last_name', 'first_name'):
        section_name = student.section or "Unassigned"
        if section_name not in sections:
            sections[section_name] = []
        sections[section_name].append(student)
    
    # Get unique values for filters
    all_tracks = Student.objects.exclude(track_strand__isnull=True).exclude(track_strand='').values_list('track_strand', flat=True).distinct().order_by('track_strand')
    all_sections = Student.objects.exclude(section__isnull=True).exclude(section='').values_list('section', flat=True).distinct().order_by('section')
    
    context = {
        'sections': sections,
        'level_filter': level_filter,
        'track_filter': track_filter,
        'section_filter': section_filter,
        'all_tracks': all_tracks,
        'all_sections': all_sections,
        'total_students': students.count(),
    }
    return render(request, 'students/sectioning.html', context)


@login_required
def update_section(request): 
    """Update student's section and track/strand from sectioning page"""
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        student = get_object_or_404(Student, id=student_id)
        
        student.track_strand = request.POST.get("track_strand", "")
        student.section = request.POST.get("section", "")
        student.save()
        
        messages.success(request, f"Updated section for {student.first_name} {student.last_name}")
    
    return redirect("students:student_sectioning")


@login_required
def payment_history(request, student_id):
    """View and manage payment history for a student"""
    student = get_object_or_404(Student, id=student_id)

    # Get all payments ordered by date (newest first)
    payments = TuitionPayment.objects.filter(
        student=student
    ).order_by('-date')

    # Calculate totals
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate expected tuition based on level and enrollment status
    expected_tuition = get_tuition_fee(student)

    context = {
        'student': student,
        'payments': payments,
        'total_paid': total_paid,
        'expected_tuition': expected_tuition,
        'payment_count': payments.count(),
    }
    
    return render(request, 'students/payment_history.html', context)


@login_required
def update_tuition_amount(request, student_id):
    """Update the total tuition amount for a student"""
    student = get_object_or_404(Student, id=student_id)

    # Get current expected tuition based on level and enrollment status
    current_tuition = get_tuition_fee(student)

    # Get total paid
    total_paid = TuitionPayment.objects.filter(
        student=student
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    if request.method == "POST":
        try:
            new_tuition = Decimal(request.POST.get("tuition_amount", 0))
        except Exception:
            messages.error(request, "Invalid tuition amount.")
            return redirect("students:update_tuition_amount", student_id=student.id)
        
        if new_tuition < 0:
            messages.error(request, "Tuition amount cannot be negative.")
            return redirect("students:update_tuition_amount", student_id=student.id)
        
        # Calculate new balance based on the new tuition amount
        new_balance = new_tuition - total_paid
        
        # Update student with custom tuition and balance
        student.custom_tuition_fee = new_tuition
        student.tuition_balance = new_balance
        student.save()
        
        messages.success(
            request, 
            f"Tuition updated to ₱{new_tuition:.2f}. New balance: ₱{new_balance:.2f}"
        )
        return redirect("students:student_statement", student_id=student.id)
    
    context = {
        'student': student,
        'current_tuition': current_tuition,
        'total_paid': total_paid,
        'current_balance': student.tuition_balance,
        'new_balance_preview': current_tuition - total_paid,
    }
    
    return render(request, 'students/update_tuition_amount.html', context)


@login_required
def students_with_tours(request):
    """View students enrolled in educational tours"""
    
    enrollments = TourEnrollment.objects.select_related(
        'student', 'tour'
    ).order_by('student__last_name', 'student__first_name', '-enrollment_date')
    
    context = {
        'enrollments': enrollments,
    }
    
    return render(request, 'students/students_with_tours.html', context)


@login_required
def printable_sections(request):
    """View all sections with option to print each one - EXCLUDE unassigned students"""
    
    # Get students with BOTH section AND track/strand assigned
    students = Student.objects.exclude(
        section__isnull=True
    ).exclude(
        section=''
    ).exclude(
        track_strand__isnull=True
    ).exclude(
        track_strand=''
    ).order_by('section', 'track_strand', 'last_name', 'first_name')
    
    # Group by section and track/strand
    sections_data = {}
    
    for student in students:
        section_name = student.section
        track_strand = student.track_strand
        
        # Create unique key for section + track combination
        key = f"{section_name}|{track_strand}"
        
        if key not in sections_data:
            sections_data[key] = {
                'section': section_name,
                'track_strand': track_strand,
                'level_type': student.level_type,
                'students': []
            }
        
        sections_data[key]['students'].append(student)
    
    # Convert to list and sort
    sections_list = sorted(sections_data.values(), key=lambda x: (x['section'], x['track_strand']))
    
    context = {
        'sections_list': sections_list,
        'total_sections': len(sections_list),
        'school_year': '2024-2025',
    }
    
    return render(request, 'students/printable_sections.html', context)


@login_required
def print_single_section(request, section_name, track_strand):
    """Print a single section with its students"""
    
    # Decode URL parameters
    from urllib.parse import unquote
    section_name = unquote(section_name)
    track_strand = unquote(track_strand)
    
    # Get students for this specific section and track
    students = Student.objects.filter(
        section=section_name,
        track_strand=track_strand
    ).order_by('last_name', 'first_name')
    
    # Get level type from first student
    level_type = students.first().level_type if students.exists() else "N/A"
    
    context = {
        'section_name': section_name,
        'track_strand': track_strand,
        'level_type': level_type,
        'students': students,
        'student_count': students.count(),
        'school_year': '2024-2025',
        'print_date': timezone.now(),
    }
    
    return render(request, 'students/print_single_section.html', context)


@login_required
def auto_update_grades(request):
    """Manual trigger to auto-update student grades from Grade 11 to 12"""
    
    if request.method == "POST":
        action = request.POST.get("action", "")
        
        if action == "preview":
            # Preview which students will be updated
            grade_11_students = Student.objects.filter(
                level_type='SHS',
                shs_grade='11',
                enrollment_status__in=['New', 'Continuing']
            ).order_by('last_name', 'first_name')
            
            context = {
                'students': grade_11_students,
                'count': grade_11_students.count(),
                'action': 'preview',
            }
            return render(request, 'students/auto_update_grades.html', context)
        
        elif action == "confirm":
            # Actually update the grades
            grade_11_students = Student.objects.filter(
                level_type='SHS',
                shs_grade='11',
                enrollment_status__in=['New', 'Continuing']
            )
            
            updated_count = 0
            for student in grade_11_students:
                student.shs_grade = '12'
                student.enrollment_status = 'Continuing'
                student.save()
                updated_count += 1
            
            messages.success(
                request, 
                f'Successfully updated {updated_count} students from Grade 11 to Grade 12!'
            )
            return redirect('students:student_list')
    
    # Show confirmation page
    grade_11_count = Student.objects.filter(
        level_type='SHS',
        shs_grade='11',
        enrollment_status__in=['New', 'Continuing']
    ).count()
    
    context = {
        'grade_11_count': grade_11_count,
        'action': 'confirm',
    }
    return render(request, 'students/auto_update_grades.html', context)


@login_required
@require_POST
def update_student_quick(request):
    """Quick update student info from modal"""
    try:
        student_id = request.POST.get('student_id')
        track_strand = request.POST.get('track_strand', '')
        section = request.POST.get('section', '')
        shs_grade = request.POST.get('shs_grade', '')
        college_year = request.POST.get('college_year', '')
        
        # Get the student
        student = Student.objects.get(id=student_id)
        
        # Update fields
        if track_strand:
            student.track_strand = track_strand
        if section:
            student.section = section
        if shs_grade:
            student.shs_grade = shs_grade
        if college_year:
            student.college_year = college_year
        
        student.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully updated {student.first_name} {student.last_name}'
        })
    
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Student not found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
def tuition_receipt_modal(request, payment_id):
    """Return tuition receipt as JSON for modal display"""
    from django.http import JsonResponse

    try:
        payment = get_object_or_404(TuitionPayment, id=payment_id)
        student = payment.student

        # Calculate tuition fee and breakdown based on level and enrollment status
        tuition_fee = get_tuition_fee(student)
        breakdown = get_tuition_breakdown(student)

        # Calculate totals
        total_paid = TuitionPayment.objects.filter(student=student).aggregate(Sum("amount"))["amount__sum"] or 0
        balance = tuition_fee - total_paid
        
        # Render receipt HTML
        receipt_html = render_to_string('students/receipt_content.html', {
            'payment': payment,
            'student': student,
            'tuition_fee': tuition_fee,
            'total_paid': total_paid,
            'balance': balance,
            'breakdown': breakdown,
        })
        
        return JsonResponse({
            'success': True,
            'receipt_html': receipt_html,
            'student_name': f"{student.first_name} {student.last_name}",
            'amount': float(payment.amount),
        })
    
    except TuitionPayment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Payment not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def update_grade(request, student_id):
    """Update student's grade level"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == "POST":
        level_type = request.POST.get("level_type")
        shs_grade = request.POST.get("shs_grade")
        college_year = request.POST.get("college_year")
        section = request.POST.get("section")
        
        student.level_type = level_type
        student.section = section
        
        if level_type == "SHS":
            student.shs_grade = shs_grade
            student.college_year = None
            if shs_grade == "11":
                student.current_grade_level = "Grade 11"
            elif shs_grade == "12":
                student.current_grade_level = "Grade 12"
        elif level_type == "COL":
            student.college_year = college_year
            student.shs_grade = None
            if college_year:
                student.current_grade_level = f"College {college_year}st Year" if college_year == "1" else f"College {college_year}nd Year" if college_year == "2" else f"College {college_year}rd Year" if college_year == "3" else f"College {college_year}th Year"
        elif level_type == "BUN":
            student.college_year = college_year
            student.shs_grade = None
            if college_year == "1":
                student.current_grade_level = "College 1st Year"
            elif college_year == "2":
                student.current_grade_level = "College 2nd Year"
        
        student.save()
        
        messages.success(request, f"Grade updated for {student.first_name} {student.last_name}")
        return redirect("students:student_list")
    
    return render(request, "students/update_grade.html", {"student": student})


# Year Level Management Functions (from the artifacts)
@login_required
def year_level_management(request):
    """Comprehensive year level management page"""
    students = Student.objects.filter(
        Q(level_type='SHS') | Q(level_type='BUN')
    ).order_by('current_grade_level', 'section', 'last_name')
    
    grade_11_count = students.filter(level_type='SHS', current_grade_level='Grade 11').count()
    grade_12_count = students.filter(level_type='SHS', current_grade_level='Grade 12').count()
    bundled_1st_count = students.filter(level_type='BUN', college_year='1').count()
    bundled_2nd_count = students.filter(level_type='BUN', college_year='2').count()
    
    students_by_level = {}
    
    grade_11_students = students.filter(level_type='SHS', current_grade_level='Grade 11')
    if grade_11_students.exists():
        students_by_level['Grade 11'] = list(grade_11_students)
    
    grade_12_students = students.filter(level_type='SHS', current_grade_level='Grade 12')
    if grade_12_students.exists():
        students_by_level['Grade 12'] = list(grade_12_students)
    
    bundled_1st = students.filter(level_type='BUN', college_year='1')
    if bundled_1st.exists():
        students_by_level['1st Year'] = list(bundled_1st)
    
    bundled_2nd = students.filter(level_type='BUN', college_year='2')
    if bundled_2nd.exists():
        students_by_level['2nd Year'] = list(bundled_2nd)
    
    context = {
        'students': students,
        'students_by_level': students_by_level,
        'grade_11_count': grade_11_count,
        'grade_12_count': grade_12_count,
        'first_year_count': bundled_1st_count,
        'second_year_count': bundled_2nd_count,
        'total_students': students.count()
    }
    
    return render(request, 'students/year_level_management.html', context)


@login_required
def auto_promote_students(request):
    """Automatically promote students to next year level"""
    if request.method == 'POST':
        promote_type = request.POST.get('promote_type')
        promoted_count = 0
        graduated_count = 0
        
        try:
            if promote_type == 'shs' or promote_type == 'all':
                grade_11_students = Student.objects.filter(level_type='SHS', current_grade_level='Grade 11')
                for student in grade_11_students:
                    student.current_grade_level = 'Grade 12'
                    student.shs_grade = '12'
                    student.enrollment_status = 'Continuing'
                    student.save()
                    promoted_count += 1
                
                grade_12_students = Student.objects.filter(level_type='SHS', current_grade_level='Grade 12')
                for student in grade_12_students:
                    student.enrollment_status = 'Graduated'
                    student.save()
                    graduated_count += 1
            
            if promote_type == 'bundled' or promote_type == 'all':
                first_year_students = Student.objects.filter(level_type='BUN', college_year='1')
                for student in first_year_students:
                    student.college_year = '2'
                    student.current_grade_level = 'College 2nd Year'
                    student.enrollment_status = 'Continuing'
                    student.save()
                    promoted_count += 1
                
                second_year_students = Student.objects.filter(level_type='BUN', college_year='2')
                for student in second_year_students:
                    student.enrollment_status = 'Graduated'
                    student.save()
                    graduated_count += 1
            
            messages.success(request, f'Successfully promoted {promoted_count} students and marked {graduated_count} as graduated!')
            
        except Exception as e:
            messages.error(request, f'Error during promotion: {str(e)}')
        
        return redirect('students:year_level_management')
    
    return redirect('students:year_level_management')


@login_required
def bulk_update_year_level(request):
    """Bulk update specific students' year levels"""
    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids')
        new_level = request.POST.get('new_level')
        
        if not student_ids or not new_level:
            messages.error(request, 'Please select students and a new year level.')
            return redirect('students:year_level_management')
        
        try:
            updated_count = 0
            for student_id in student_ids:
                student = Student.objects.get(id=student_id)
                student.current_grade_level = new_level
                
                if new_level == 'Grade 11':
                    student.shs_grade = '11'
                    student.level_type = 'SHS'
                elif new_level == 'Grade 12':
                    student.shs_grade = '12'
                    student.level_type = 'SHS'
                elif new_level == '1st Year':
                    student.college_year = '1'
                    student.level_type = 'BUN'
                    student.current_grade_level = 'College 1st Year'
                elif new_level == '2nd Year':
                    student.college_year = '2'
                    student.level_type = 'BUN'
                    student.current_grade_level = 'College 2nd Year'
                
                student.save()
                updated_count += 1
            
            messages.success(request, f'Successfully updated {updated_count} students to {new_level}')
        except Exception as e:
            messages.error(request, f'Error updating students: {str(e)}')
        
        return redirect('students:year_level_management')
    
    return redirect('students:year_level_management')


@login_required
def reset_sections(request):
    """Clear all sections for new school year"""
    if request.method == 'POST':
        confirm = request.POST.get('confirm')

        if confirm == 'yes':
            try:
                Student.objects.filter(Q(level_type='SHS') | Q(level_type='BUN')).update(section=None)
                messages.success(request, 'All sections have been cleared for the new school year.')
            except Exception as e:
                messages.error(request, f'Error clearing sections: {str(e)}')

        return redirect('students:year_level_management')

    return redirect('students:year_level_management')


@login_required
def bulk_assign_section(request):
    """Bulk assign sections to multiple students based on filters"""
    if request.method == "POST":
        # Get filter criteria
        filter_level_type = request.POST.get("filter_level_type", "")
        filter_track_strand = request.POST.get("filter_track_strand", "")
        filter_year_level = request.POST.get("filter_year_level", "")
        only_unassigned = request.POST.get("only_unassigned", "yes") == "yes"

        # Get assignment values
        assign_track_strand = request.POST.get("assign_track_strand", "")
        assign_section = request.POST.get("assign_section", "")

        if not assign_track_strand and not assign_section:
            return JsonResponse({
                'success': False,
                'error': 'Please provide at least one value to assign (track/strand or section)'
            }, status=400)

        # Build queryset with filters
        students = Student.objects.all()

        if filter_level_type:
            students = students.filter(level_type=filter_level_type)
        if filter_track_strand:
            students = students.filter(track_strand=filter_track_strand)
        if filter_year_level:
            students = students.filter(year_level=filter_year_level)
        if only_unassigned:
            students = students.filter(Q(section__isnull=True) | Q(section=''))

        # Perform bulk update
        update_fields = {}
        if assign_track_strand:
            update_fields['track_strand'] = assign_track_strand
        if assign_section:
            update_fields['section'] = assign_section

        updated_count = students.update(**update_fields)

        return JsonResponse({
            'success': True,
            'message': f'Successfully updated {updated_count} students',
            'updated_count': updated_count
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@login_required
def get_section_stats(request):
    """Get statistics about sections for dashboard/analytics"""
    # Get all students with sections
    students = Student.objects.all()

    # Overall stats
    total_students = students.count()
    assigned_students = students.exclude(Q(section__isnull=True) | Q(section='')).count()
    unassigned_students = total_students - assigned_students

    # Stats by level type
    level_stats = {}
    for level in ['SHS', 'COL', 'BUN']:
        level_students = students.filter(level_type=level)
        level_stats[level] = {
            'total': level_students.count(),
            'assigned': level_students.exclude(Q(section__isnull=True) | Q(section='')).count(),
            'unassigned': level_students.filter(Q(section__isnull=True) | Q(section='')).count()
        }

    # Section breakdown
    sections = students.exclude(
        Q(section__isnull=True) | Q(section='')
    ).values('section', 'track_strand', 'level_type').annotate(
        count=Count('id')
    ).order_by('section', 'track_strand')

    # Track/Strand breakdown
    track_stats = students.exclude(
        Q(track_strand__isnull=True) | Q(track_strand='')
    ).values('track_strand').annotate(
        count=Count('id')
    ).order_by('track_strand')

    # Get unique sections and tracks for filters
    unique_sections = list(students.exclude(
        Q(section__isnull=True) | Q(section='')
    ).values_list('section', flat=True).distinct().order_by('section'))

    unique_tracks = list(students.exclude(
        Q(track_strand__isnull=True) | Q(track_strand='')
    ).values_list('track_strand', flat=True).distinct().order_by('track_strand'))

    return JsonResponse({
        'success': True,
        'stats': {
            'total_students': total_students,
            'assigned_students': assigned_students,
            'unassigned_students': unassigned_students,
            'level_stats': level_stats,
            'sections': list(sections),
            'track_stats': list(track_stats),
            'unique_sections': unique_sections,
            'unique_tracks': unique_tracks
        }
    })


@login_required
def auto_assign_sections(request):
    """Auto-assign sections to students based on track/strand and capacity"""
    if request.method == "POST":
        level_type = request.POST.get("level_type", "")
        track_strand = request.POST.get("track_strand", "")
        max_per_section = int(request.POST.get("max_per_section", 40))
        section_prefix = request.POST.get("section_prefix", "")

        if not level_type:
            return JsonResponse({
                'success': False,
                'error': 'Level type is required'
            }, status=400)

        # Get unassigned students matching criteria
        students = Student.objects.filter(
            level_type=level_type
        ).filter(
            Q(section__isnull=True) | Q(section='')
        ).order_by('last_name', 'first_name')

        if track_strand:
            students = students.filter(track_strand=track_strand)

        if not students.exists():
            return JsonResponse({
                'success': False,
                'error': 'No unassigned students found matching criteria'
            }, status=400)

        # Group students by track/strand for section assignment
        track_groups = {}
        for student in students:
            track = student.track_strand or "General"
            if track not in track_groups:
                track_groups[track] = []
            track_groups[track].append(student)

        # Assign sections
        total_assigned = 0
        section_assignments = {}

        for track, track_students in track_groups.items():
            section_num = 1
            current_section_count = 0

            # Check existing sections for this track to continue numbering
            existing_sections = Student.objects.filter(
                level_type=level_type,
                track_strand=track
            ).exclude(
                Q(section__isnull=True) | Q(section='')
            ).values_list('section', flat=True).distinct()

            # Find the highest section number
            for sec in existing_sections:
                try:
                    # Try to extract number from section name
                    sec_clean = sec.replace(section_prefix, '').strip()
                    if sec_clean.isdigit():
                        section_num = max(section_num, int(sec_clean) + 1)
                    elif len(sec_clean) == 1 and sec_clean.isalpha():
                        section_num = max(section_num, ord(sec_clean.upper()) - ord('A') + 2)
                except:
                    pass

            for student in track_students:
                if current_section_count >= max_per_section:
                    section_num += 1
                    current_section_count = 0

                # Generate section name
                if section_prefix:
                    section_name = f"{section_prefix}{section_num}"
                else:
                    # Use letters A, B, C... if no prefix
                    section_name = chr(ord('A') + section_num - 1)

                student.section = section_name
                student.save()

                current_section_count += 1
                total_assigned += 1

                # Track assignments for response
                key = f"{track} - {section_name}"
                if key not in section_assignments:
                    section_assignments[key] = 0
                section_assignments[key] += 1

        return JsonResponse({
            'success': True,
            'message': f'Successfully assigned {total_assigned} students to sections',
            'total_assigned': total_assigned,
            'assignments': section_assignments
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)