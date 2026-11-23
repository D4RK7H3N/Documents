# assesment/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from decimal import Decimal
from .models import AssessmentType, StudentAssessment, AssessmentPayment, AssessmentBatch
from students.models import Student
from django.utils import timezone


@login_required
def assessment_dashboard(request):
    """
    Main dashboard showing all students with assessments
    """
    search_query = request.GET.get('search', '')
    assessment_filter = request.GET.get('assessment', '')
    status_filter = request.GET.get('status', '')
    level_filter = request.GET.get('level', '')
    
    # Get all student assessments
    assessments = StudentAssessment.objects.select_related(
        'student', 'assessment_type'
    ).prefetch_related('payments')
    
    # Apply filters
    if search_query:
        assessments = assessments.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__lrn__icontains=search_query)
        )
    
    if assessment_filter:
        assessments = assessments.filter(assessment_type_id=assessment_filter)
    
    if status_filter:
        assessments = assessments.filter(status=status_filter)
    
    if level_filter:
        assessments = assessments.filter(student__level_type=level_filter)
    
    # Order by balance (highest first)
    assessments = assessments.order_by('-balance', 'student__last_name')
    
    # Get active assessment types for filter
    assessment_types = AssessmentType.objects.filter(is_active=True)
    
    # Calculate summary
    total_assessments = assessments.count()
    total_collected = assessments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_balance = assessments.aggregate(Sum('balance'))['balance__sum'] or 0
    students_with_balance = assessments.filter(balance__gt=0).count()
    
    context = {
        'assessments': assessments,
        'assessment_types': assessment_types,
        'search_query': search_query,
        'assessment_filter': assessment_filter,
        'status_filter': status_filter,
        'level_filter': level_filter,
        'total_assessments': total_assessments,
        'total_collected': total_collected,
        'total_balance': total_balance,
        'students_with_balance': students_with_balance,
    }
    
    return render(request, 'assessment/dashboard.html', context)


@login_required
def assessment_detail(request, assessment_id):
    """
    View specific student's assessment with payment history
    """
    assessment = get_object_or_404(
        StudentAssessment.objects.select_related('student', 'assessment_type'),
        id=assessment_id
    )
    
    # Get all payments
    payments = assessment.payments.all().order_by('-payment_date')
    
    # Calculate remaining balance
    remaining_balance = assessment.total_fee
    payments_with_balance = []
    for payment in payments:
        payment.remaining_balance = remaining_balance - payment.amount
        remaining_balance -= payment.amount
        payments_with_balance.append(payment)
    
    context = {
        'assessment': assessment,
        'payments': payments_with_balance,
        'student': assessment.student,
        'assessment_type': assessment.assessment_type,
        'has_balance': assessment.balance > 0,
    }
    
    return render(request, 'assessment/detail.html', context)


@login_required
def process_assessment_payment(request, assessment_id):
    """
    Process payment for an assessment
    """
    assessment = get_object_or_404(StudentAssessment, id=assessment_id)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
        except:
            messages.error(request, "Invalid payment amount.")
            return redirect('assessment:process_payment', assessment_id=assessment.id)
        
        payment_method = request.POST.get('payment_method', 'Cash')
        reference_number = request.POST.get('reference_number', '')
        gcash_number = request.POST.get('gcash_number', '')
        remarks = request.POST.get('remarks', '')
        
        # Validation
        if amount <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect('assessment:process_payment', assessment_id=assessment.id)
        
        if amount > assessment.balance:
            messages.error(
                request, 
                f"Payment amount (₱{amount:.2f}) exceeds remaining balance (₱{assessment.balance:.2f})."
            )
            return redirect('assessment:process_payment', assessment_id=assessment.id)
        
        # Create payment
        payment = AssessmentPayment.objects.create(
            assessment=assessment,
            student=assessment.student,
            assessment_type=assessment.assessment_type,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number,
            gcash_number=gcash_number,
            received_by=request.user.get_full_name() or request.user.username,
            remarks=remarks,
        )
        
        messages.success(
            request, 
            f"Payment of ₱{amount:.2f} recorded successfully for {assessment.assessment_type.name}!"
        )
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'payment_id': payment.id,
                'new_balance': float(assessment.balance),
                'amount_paid': float(assessment.amount_paid),
            })
        
        return redirect('assessment:payment_receipt', payment_id=payment.id)
    
    context = {
        'assessment': assessment,
        'student': assessment.student,
        'assessment_type': assessment.assessment_type,
    }
    return render(request, 'assessment/process_payment.html', context)


@login_required
def payment_receipt(request, payment_id):
    """
    Print assessment payment receipt
    """
    payment = get_object_or_404(AssessmentPayment, id=payment_id)
    assessment = payment.assessment
    
    # Calculate remaining balance at time of payment
    previous_payments = assessment.payments.filter(
        payment_date__lt=payment.payment_date
    )
    previous_total = previous_payments.aggregate(Sum('amount'))['amount__sum'] or 0
    payment.remaining_balance = assessment.total_fee - previous_total - payment.amount
    
    context = {
        'payment': payment,
        'assessment': assessment,
        'student': assessment.student,
        'assessment_type': assessment.assessment_type,
    }
    return render(request, 'assessment/receipt.html', context)


@login_required
def student_assessments(request, student_id):
    """
    View all assessments for a specific student
    """
    student = get_object_or_404(Student, id=student_id)
    
    assessments = StudentAssessment.objects.filter(
        student=student
    ).select_related('assessment_type').prefetch_related('payments').order_by('-date_assessed')
    
    # Calculate totals
    total_fees = assessments.aggregate(Sum('total_fee'))['total_fee__sum'] or 0
    total_paid = assessments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_balance = assessments.aggregate(Sum('balance'))['balance__sum'] or 0
    
    context = {
        'student': student,
        'assessments': assessments,
        'total_fees': total_fees,
        'total_paid': total_paid,
        'total_balance': total_balance,
    }
    
    return render(request, 'assessment/student_assessments.html', context)


@login_required
def assessment_statement(request, assessment_id):
    """
    Printable statement of account for assessment
    """
    assessment = get_object_or_404(
        StudentAssessment.objects.select_related('student', 'assessment_type'),
        id=assessment_id
    )
    
    # Get all payments
    payments = assessment.payments.all().order_by('payment_date')
    
    # Add remaining balance
    remaining_balance = assessment.total_fee
    payments_with_balance = []
    for payment in payments:
        remaining_balance -= payment.amount
        payment.remaining_balance = remaining_balance
        payments_with_balance.append(payment)
    
    context = {
        'assessment': assessment,
        'student': assessment.student,
        'assessment_type': assessment.assessment_type,
        'payments': payments_with_balance,
        'current_date': timezone.now(),
    }
    
    return render(request, 'assessment/statement.html', context)

@login_required
def manage_assessment_types(request):
    """
    Manage assessment types (Admin only)
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('assessment:dashboard')
    
    assessment_types = AssessmentType.objects.all().order_by('name')
    
    context = {
        'assessment_types': assessment_types,
    }
    return render(request, 'assessment/manage_types.html', context)


@login_required
def create_assessment_type(request):
    """
    Create new assessment type (Admin only)
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('assessment:dashboard')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            code = request.POST.get('code').upper()
            category = request.POST.get('category')
            description = request.POST.get('description', '')
            amount = Decimal(request.POST.get('amount', 0))
            applicable_to = request.POST.get('applicable_to')
            applicable_tracks = request.POST.get('applicable_tracks', '')
            is_required = request.POST.get('is_required') == 'on'
            
            assessment_type = AssessmentType.objects.create(
                name=name,
                code=code,
                category=category,
                description=description,
                amount=amount,
                applicable_to=applicable_to,
                applicable_tracks=applicable_tracks,
                is_required=is_required,
            )
            
            messages.success(request, f"Assessment type '{assessment_type.name}' created successfully!")
            return redirect('assessment:manage_types')
            
        except Exception as e:
            messages.error(request, f"Error creating assessment type: {str(e)}")
    
    context = {
        'categories': AssessmentType.CATEGORY_CHOICES,
        'applicable_to_choices': AssessmentType.APPLICABLE_TO_CHOICES,
    }
    return render(request, 'assessment/create_type.html', context)


@login_required
def assign_assessment(request, student_id):
    """
    Assign an assessment to a student (Admin only)
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('assessment:dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        try:
            assessment_type_id = request.POST.get('assessment_type')
            assessment_type = get_object_or_404(AssessmentType, id=assessment_type_id)
            
            # Check if already assigned
            if StudentAssessment.objects.filter(student=student, assessment_type=assessment_type).exists():
                messages.warning(request, f"{student.first_name} already has this assessment assigned.")
                return redirect('assessment:student_assessments', student_id=student.id)
            
            # Custom amount or default
            custom_amount = request.POST.get('custom_amount', '')
            total_fee = Decimal(custom_amount) if custom_amount else assessment_type.amount
            
            due_date = request.POST.get('due_date', None)
            notes = request.POST.get('notes', '')
            
            # Create assessment
            assessment = StudentAssessment.objects.create(
                student=student,
                assessment_type=assessment_type,
                total_fee=total_fee,
                balance=total_fee,
                due_date=due_date if due_date else None,
                notes=notes,
                assessed_by=request.user.get_full_name() or request.user.username,
            )
            
            messages.success(
                request, 
                f"{assessment_type.name} (₱{total_fee:.2f}) assigned to {student.first_name} {student.last_name}"
            )
            return redirect('assessment:student_assessments', student_id=student.id)
            
        except Exception as e:
            messages.error(request, f"Error assigning assessment: {str(e)}")
    
    # Get applicable assessment types for this student
    assessment_types = AssessmentType.objects.filter(
        is_active=True
    ).filter(
        Q(applicable_to='ALL') | Q(applicable_to=student.level_type)
    )
    
    context = {
        'student': student,
        'assessment_types': assessment_types,
    }
    return render(request, 'assessmen/assign_assessment.html', context)


@login_required
def batch_assign_assessment(request):
    """
    Batch assign assessment to multiple students (Admin only)
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('assessment:dashboard')
    
    if request.method == 'POST':
        try:
            assessment_type_id = request.POST.get('assessment_type')
            assessment_type = get_object_or_404(AssessmentType, id=assessment_type_id)
            
            level_type = request.POST.get('level_type')
            track_strand = request.POST.get('track_strand', '')
            section = request.POST.get('section', '')
            
            # Get students based on criteria
            students = Student.objects.filter(level_type=level_type)
            
            if track_strand:
                students = students.filter(track_strand=track_strand)
            
            if section:
                students = students.filter(section=section)
            
            # Create assessments
            created_count = 0
            skipped_count = 0
            
            for student in students:
                # Check if already has this assessment
                if not StudentAssessment.objects.filter(
                    student=student, 
                    assessment_type=assessment_type
                ).exists():
                    StudentAssessment.objects.create(
                        student=student,
                        assessment_type=assessment_type,
                        total_fee=assessment_type.amount,
                        balance=assessment_type.amount,
                        assessed_by=request.user.get_full_name() or request.user.username,
                    )
                    created_count += 1
                else:
                    skipped_count += 1
            
            # Create batch record
            batch_name = f"{assessment_type.name} - {level_type}"
            if track_strand:
                batch_name += f" {track_strand}"
            if section:
                batch_name += f" {section}"
            
            AssessmentBatch.objects.create(
                name=batch_name,
                assessment_type=assessment_type,
                level_type=level_type,
                track_strand=track_strand,
                section=section,
                students_count=created_count,
                total_amount=assessment_type.amount * created_count,
                created_by=request.user.get_full_name() or request.user.username,
            )
            
            messages.success(
                request, 
                f"Assessment assigned to {created_count} student(s). "
                f"{skipped_count} already had this assessment."
            )
            return redirect('assessment:dashboard')
            
        except Exception as e:
            messages.error(request, f"Error in batch assignment: {str(e)}")
    
    # Get form data
    assessment_types = AssessmentType.objects.filter(is_active=True)
    tracks = Student.objects.exclude(track_strand__isnull=True).exclude(
        track_strand=''
    ).values_list('track_strand', flat=True).distinct()
    sections = Student.objects.exclude(section__isnull=True).exclude(
        section=''
    ).values_list('section', flat=True).distinct()
    
    context = {
        'assessment_types': assessment_types,
        'tracks': tracks,
        'sections': sections,
    }
    return render(request, 'assessment/batch_assign.html', context)