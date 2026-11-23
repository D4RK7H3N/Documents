from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from decimal import Decimal
import json
from django.http import JsonResponse
from .models import EducationalTour, TourEnrollment, TourPayment
from students.models import Student
from django.utils import timezone


@login_required
def tour_payment_dashboard(request):
    """
    Main dashboard - Show all students with tour payments
    Separated into Regular (Grade 11) and Payee (BUN) students
    """
    search_query = request.GET.get('search', '')
    level_filter = request.GET.get('level', '')
    track_filter = request.GET.get('track', '')
    section_filter = request.GET.get('section', '')
    payment_status = request.GET.get('status', '')
    
    # Get all enrollments
    enrollments = TourEnrollment.objects.select_related(
        'student', 'tour'
    ).prefetch_related('payments')
    
    # Apply filters
    if search_query:
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__lrn__icontains=search_query)
        )
    
    if level_filter:
        enrollments = enrollments.filter(student__level_type=level_filter)
    
    if track_filter:
        enrollments = enrollments.filter(student__track_strand=track_filter)
    
    if section_filter:
        enrollments = enrollments.filter(student__section=section_filter)
    
    if payment_status:
        enrollments = enrollments.filter(status=payment_status)
    
    # Separate into Regular (Grade 11) and Payee (BUN with section and track)
    regular_students = enrollments.filter(
        student__current_grade_level='Grade 11'
    ).order_by('student__section', 'student__last_name')
    
    payee_students = enrollments.filter(
        student__level_type='BUN'
    ).exclude(
        student__section__isnull=True
    ).exclude(
        student__section=''
    ).exclude(
        student__track_strand__isnull=True
    ).exclude(
        student__track_strand=''
    ).order_by('student__section', 'student__last_name')
    
    # Get filter options
    tracks = Student.objects.exclude(
        track_strand__isnull=True
    ).exclude(
        track_strand=''
    ).values_list('track_strand', flat=True).distinct().order_by('track_strand')
    
    sections = Student.objects.exclude(
        section__isnull=True
    ).exclude(
        section=''
    ).values_list('section', flat=True).distinct().order_by('section')
    
    # Calculate totals
    total_regular = regular_students.count()
    total_payee = payee_students.count()
    total_collected = enrollments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    total_balance = enrollments.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
    
    context = {
        'regular_students': regular_students,
        'payee_students': payee_students,
        'total_regular': total_regular,
        'total_payee': total_payee,
        'total_collected': total_collected,
        'total_balance': total_balance,
        'search_query': search_query,
        'level_filter': level_filter,
        'track_filter': track_filter,
        'section_filter': section_filter,
        'payment_status': payment_status,
        'tracks': tracks,
        'sections': sections,
    }
    
    return render(request, 'tours/payment_dashboard.html', context)


@login_required
def section_list_view(request):
    """
    View students organized by section with payment status
    """
    level_filter = request.GET.get('level', 'SHS')
    track_filter = request.GET.get('track', '')
    section_filter = request.GET.get('section', '')
    student_type = request.GET.get('type', 'all')
    
    # Get students
    students = Student.objects.all()
    
    if level_filter:
        students = students.filter(level_type=level_filter)
    
    if track_filter:
        students = students.filter(track_strand=track_filter)
    
    if section_filter:
        students = students.filter(section=section_filter)
    
    # Filter by student type
    if student_type == 'regular':
        students = students.filter(current_grade_level='Grade 11')
    elif student_type == 'payee':
        students = students.filter(
            level_type='BUN'
        ).exclude(
            section__isnull=True
        ).exclude(
            section=''
        ).exclude(
            track_strand__isnull=True
        ).exclude(
            track_strand=''
        )
    
    # Annotate with tour enrollment info
    students = students.annotate(
        tour_enrollment_count=Count('tour_enrollments'),
        tour_balance=Sum('tour_enrollments__balance')
    ).order_by('section', 'last_name', 'first_name')
    
    # Group by section
    sections_dict = {}
    for student in students:
        section_name = student.section or "Unassigned"
        if section_name not in sections_dict:
            sections_dict[section_name] = {
                'students': [],
                'total_students': 0,
                'with_tours': 0,
                'total_balance': Decimal('0.00'),
            }
        
        sections_dict[section_name]['students'].append(student)
        sections_dict[section_name]['total_students'] += 1
        if student.tour_enrollment_count > 0:
            sections_dict[section_name]['with_tours'] += 1
        sections_dict[section_name]['total_balance'] += student.tour_balance or Decimal('0.00')
    
    # Get filter options
    tracks = Student.objects.exclude(
        track_strand__isnull=True
    ).exclude(
        track_strand=''
    ).values_list('track_strand', flat=True).distinct().order_by('track_strand')
    
    sections = Student.objects.exclude(
        section__isnull=True
    ).exclude(
        section=''
    ).values_list('section', flat=True).distinct().order_by('section')
    
    context = {
        'sections': sections_dict,
        'level_filter': level_filter,
        'track_filter': track_filter,
        'section_filter': section_filter,
        'student_type': student_type,
        'tracks': tracks,
        'available_sections': sections,
        'total_students': students.count(),
    }
    
    return render(request, 'tours/section_list_view.html', context)


@login_required
def print_section_list(request):
    """
    Printable section list with student details
    """
    section = request.GET.get('section', '')
    track = request.GET.get('track', '')
    level = request.GET.get('level', 'SHS')
    student_type = request.GET.get('type', 'all')
    include_tours = request.GET.get('include_tours', 'yes') == 'yes'
    
    # Get students
    students = Student.objects.filter(section=section) if section else Student.objects.all()
    
    if level:
        students = students.filter(level_type=level)
    
    if track:
        students = students.filter(track_strand=track)
    
    # Filter by type
    if student_type == 'regular':
        students = students.filter(current_grade_level='Grade 11')
    elif student_type == 'payee':
        students = students.filter(
            level_type='BUN'
        ).exclude(
            section__isnull=True
        ).exclude(
            section=''
        ).exclude(
            track_strand__isnull=True
        ).exclude(
            track_strand=''
        )
    
    # Annotate with tour info if needed
    if include_tours:
        students = students.annotate(
            tour_count=Count('tour_enrollments'),
            tour_balance=Sum('tour_enrollments__balance')
        )
    
    students = students.order_by('last_name', 'first_name')
    
    context = {
        'students': students,
        'section': section,
        'track': track,
        'level': level,
        'student_type': student_type,
        'include_tours': include_tours,
        'print_date': timezone.now(),
        'total_count': students.count(),
    }
    
    return render(request, 'tours/print_section_list.html', context)


@login_required
def student_payment_detail(request, enrollment_id):
    """
    View specific student's tour payment details
    """
    enrollment = get_object_or_404(
        TourEnrollment.objects.select_related('student', 'tour'),
        id=enrollment_id
    )
    
    payments = enrollment.payments.all().order_by('-payment_date')
    
    # Calculate remaining balance
    remaining_balance = enrollment.total_fee
    payments_with_balance = []
    for payment in payments:
        payment.remaining_balance = remaining_balance - payment.amount
        remaining_balance -= payment.amount
        payments_with_balance.append(payment)
    
    # Determine if regular or bundled
    is_regular = enrollment.student.current_grade_level == 'Grade 11'
    
    context = {
        'enrollment': enrollment,
        'payments': payments_with_balance,
        'student': enrollment.student,
        'tour': enrollment.tour,
        'is_regular': is_regular,
        'student_type': 'Regular Student' if is_regular else 'Bundled Student',
    }
    
    return render(request, 'tours/student_payment_detail.html', context)


@login_required
def process_tour_payment(request, enrollment_id):
    """
    Process tour payment for a student
    """
    enrollment = get_object_or_404(TourEnrollment, id=enrollment_id)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
            payment_method = request.POST.get('payment_method', 'Cash')
            reference_number = request.POST.get('reference_number', '')
            remarks = request.POST.get('remarks', '')
            
            # Validation
            if amount <= 0:
                messages.error(request, "Payment amount must be greater than zero.")
                return redirect('tours:process_payment', enrollment_id=enrollment.id)
            
            if amount > enrollment.balance:
                messages.error(
                    request,
                    f"Payment (PHP {amount:.2f}) exceeds balance (PHP {enrollment.balance:.2f})."
                )
                return redirect('tours:process_payment', enrollment_id=enrollment.id)
            
            # Create payment
            payment = TourPayment.objects.create(
                enrollment=enrollment,
                tour=enrollment.tour,
                student=enrollment.student,
                amount=amount,
                method=payment_method,
                reference_number=reference_number,
                received_by=request.user.get_full_name() or request.user.username,
                remarks=remarks,
            )
            
            messages.success(
                request,
                f"Payment of PHP {amount:.2f} recorded for {enrollment.student.first_name}!"
            )
            return redirect('tours:payment_receipt', payment_id=payment.id)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('tours:process_payment', enrollment_id=enrollment.id)
    
    # Determine if regular or bundled
    is_regular = enrollment.student.current_grade_level == 'Grade 11'
    
    context = {
        'enrollment': enrollment,
        'student': enrollment.student,
        'tour': enrollment.tour,
        'is_regular': is_regular,
    }
    return render(request, 'tours/process_payment.html', context)


@login_required
def payment_receipt(request, payment_id):
    """
    Printable receipt for tour payment
    """
    payment = get_object_or_404(TourPayment, id=payment_id)
    enrollment = payment.enrollment
    
    # Calculate remaining balance
    previous_payments = enrollment.payments.filter(
        payment_date__lt=payment.payment_date
    )
    previous_total = previous_payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    remaining_balance = enrollment.total_fee - previous_total - payment.amount
    
    is_regular = enrollment.student.current_grade_level == 'Grade 11'
    
    context = {
        'payment': payment,
        'enrollment': enrollment,
        'student': enrollment.student,
        'tour': enrollment.tour,
        'remaining_balance': remaining_balance,
        'is_regular': is_regular,
        'student_type': 'Regular Student' if is_regular else 'Bundled Student',
    }
    return render(request, 'tours/payment_receipt.html', context)


@login_required
def section_payment_summary(request):
    """
    Summary of payments by section
    """
    level_filter = request.GET.get('level', 'SHS')
    track_filter = request.GET.get('track', '')
    
    # Get all students with tour enrollments
    students = Student.objects.filter(
        tour_enrollments__isnull=False
    ).distinct()
    
    if level_filter:
        students = students.filter(level_type=level_filter)
    
    if track_filter:
        students = students.filter(track_strand=track_filter)
    
    students = students.annotate(
        tour_total=Sum('tour_enrollments__total_fee'),
        tour_paid=Sum('tour_enrollments__amount_paid'),
        tour_balance=Sum('tour_enrollments__balance')
    )
    
    # Group by section
    section_summary = {}
    for student in students:
        section = student.section or "Unassigned"
        
        if section not in section_summary:
            section_summary[section] = {
                'track': student.track_strand,
                'total_students': 0,
                'total_amount': Decimal('0.00'),
                'total_paid': Decimal('0.00'),
                'total_balance': Decimal('0.00'),
                'regular_count': 0,
                'bundled_count': 0,
            }
        
        section_summary[section]['total_students'] += 1
        section_summary[section]['total_amount'] += student.tour_total or Decimal('0.00')
        section_summary[section]['total_paid'] += student.tour_paid or Decimal('0.00')
        section_summary[section]['total_balance'] += student.tour_balance or Decimal('0.00')
        
        if student.current_grade_level == 'Grade 11':
            section_summary[section]['regular_count'] += 1
        else:
            section_summary[section]['bundled_count'] += 1
    
    # Get filter options
    tracks = Student.objects.exclude(
        track_strand__isnull=True
    ).exclude(
        track_strand=''
    ).values_list('track_strand', flat=True).distinct().order_by('track_strand')
    
    context = {
        'section_summary': section_summary,
        'level_filter': level_filter,
        'track_filter': track_filter,
        'tracks': tracks,
    }
    
    return render(request, 'tours/section_payment_summary.html', context)


@login_required
def export_section_excel(request):
    """
    Export section list to CSV
    """
    import csv
    
    section = request.GET.get('section', '')
    track = request.GET.get('track', '')
    student_type = request.GET.get('type', 'all')
    
    # Get students
    students = Student.objects.all()
    
    if section:
        students = students.filter(section=section)
    
    if track:
        students = students.filter(track_strand=track)
    
    if student_type == 'regular':
        students = students.filter(current_grade_level='Grade 11')
    elif student_type == 'payee':
        students = students.filter(
            level_type='BUN'
        ).exclude(
            section__isnull=True
        ).exclude(
            section=''
        ).exclude(
            track_strand__isnull=True
        ).exclude(
            track_strand=''
        )
    
    students = students.annotate(
        tour_balance=Sum('tour_enrollments__balance')
    ).order_by('last_name', 'first_name')
    
    # Create CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="section_{section}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['LRN', 'Last Name', 'First Name', 'Section', 'Track/Strand', 'Level', 'Type', 'Tour Balance'])
    
    for student in students:
        student_type_str = 'Regular' if student.current_grade_level == 'Grade 11' else 'Bundled'
        writer.writerow([
            student.lrn,
            student.last_name,
            student.first_name,
            student.section or '',
            student.track_strand or '',
            student.level_type,
            student_type_str,
            f"{student.tour_balance or 0:.2f}"
        ])
    
    return response


@login_required
def add_student_to_tour(request):
    """
    Quick add student to tour - organized by section
    Only shows Grade 11 (Regular) and Bundled 1st Year (Payee) students
    """
    
    if request.method == 'POST':
        tour_id = request.POST.get('tour_id')
        student_id = request.POST.get('student_id')
        
        try:
            tour = get_object_or_404(EducationalTour, id=tour_id)
            student = get_object_or_404(Student, id=student_id)
            
            # Check if already enrolled
            existing = TourEnrollment.objects.filter(tour=tour, student=student).first()
            if existing:
                return JsonResponse({
                    'success': False,
                    'message': f"{student.first_name} is already enrolled in this tour."
                })
            
            # Check if tour has slots available
            if not tour.has_slots_available():
                return JsonResponse({
                    'success': False,
                    'message': f"Tour '{tour.name}' is full."
                })
            
            # Create enrollment
            enrollment = TourEnrollment.objects.create(
                tour=tour,
                student=student,
                total_fee=tour.total_cost,
                balance=tour.total_cost,
            )
            
            return JsonResponse({
                'success': True,
                'message': f"{student.first_name} {student.last_name} has been enrolled in {tour.name}!"
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"Error: {str(e)}"
            })
    
    # GET request - show modal form
    tours = EducationalTour.objects.filter(
        status__in=['Planned', 'Ongoing']
    ).order_by('-tour_date')
    
    # Get eligible students: Grade 11 (Regular) and Bundled 1st Year (Payee)
    regular_students = Student.objects.filter(
        current_grade_level='Grade 11'
    ).exclude(
        section__isnull=True
    ).exclude(
        section=''
    ).order_by('section', 'last_name', 'first_name')
    
    payee_students = Student.objects.filter(
        level_type='BUN',
        college_year='1'
    ).exclude(
        section__isnull=True
    ).exclude(
        section=''
    ).exclude(
        track_strand__isnull=True
    ).exclude(
        track_strand=''
    ).order_by('section', 'last_name', 'first_name')
    
    # Group by section
    sections_dict = {}
    
    # Add regular students
    for student in regular_students:
        section_name = f"{student.section} (Regular)"
        if section_name not in sections_dict:
            sections_dict[section_name] = {
                'type': 'Regular',
                'students': []
            }
        sections_dict[section_name]['students'].append(student)
    
    # Add payee students
    for student in payee_students:
        section_name = f"{student.section} (Payee - 1st Year)"
        if section_name not in sections_dict:
            sections_dict[section_name] = {
                'type': 'Payee',
                'students': []
            }
        sections_dict[section_name]['students'].append(student)
    
    # Sort sections
    sections_dict = dict(sorted(sections_dict.items()))
    
    context = {
        'tours': tours,
        'sections': sections_dict,
    }
    return render(request, 'tours/add_student_modal.html', context)

@login_required
def enrollment_management(request):
    # Get filters
    level_filter = request.GET.get('level', '')
    track_filter = request.GET.get('track', '')
    section_filter = request.GET.get('section', '')
    student_type = request.GET.get('type', 'all')
    
    # Get active tours - FIXED: Changed Tour to EducationalTour
    tours = EducationalTour.objects.filter(status='Planned').order_by('tour_date')
    
    # Get eligible students (adjust based on your model)
    students = Student.objects.filter(
        # Add your filtering logic here
    )
    
    # Apply filters
    if level_filter:
        students = students.filter(level_type=level_filter)  # Changed 'level' to 'level_type' to match your model
    if track_filter:
        students = students.filter(track_strand=track_filter)
    if section_filter:
        students = students.filter(section=section_filter)
    
    # Group by section
    sections = {}
    for student in students:
        section = student.section or 'No Section'
        if section not in sections:
            sections[section] = {
                'students': [],
                'track': student.track_strand,
                'type': 'Regular' if student.current_grade_level == 'Grade 11' else 'Payee'
            }
        sections[section]['students'].append(student)
    
    context = {
        'tours': tours,
        'sections': sections,
        'level_filter': level_filter,
        'track_filter': track_filter,
        'section_filter': section_filter,
        'student_type': student_type,
        'tracks': students.values_list('track_strand', flat=True).distinct(),
        'available_sections': students.values_list('section', flat=True).distinct(),
    }
    
    return render(request, 'tours/enrollment_management.html', context)


@login_required
def bulk_enroll_students_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tour_id = data.get('tour_id')
            student_ids = data.get('student_ids', [])
            
            # FIXED: Changed Tour to EducationalTour
            tour = EducationalTour.objects.get(id=tour_id)
            enrolled_count = 0
            
            for student_id in student_ids:
                student = Student.objects.get(id=student_id)
                # Check if already enrolled
                if not TourEnrollment.objects.filter(tour=tour, student=student).exists():
                    TourEnrollment.objects.create(
                        tour=tour,
                        student=student,
                        total_fee=tour.total_cost,
                        balance=tour.total_cost,
                        status='Enrolled'
                    )
                    enrolled_count += 1
            
            return JsonResponse({
                'success': True,
                'enrolled_count': enrolled_count,
                'message': f'Successfully enrolled {enrolled_count} students!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
def get_tour_companies(request):
    """Get list of existing tour companies for autocomplete"""
    companies = EducationalTour.objects.exclude(
        tour_company__isnull=True
    ).exclude(
        tour_company=''
    ).values_list('tour_company', flat=True).distinct().order_by('tour_company')
    
    return JsonResponse({'companies': list(companies)})


@login_required
def create_tour(request):
    """Create a new educational tour"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            destination = request.POST.get('destination')
            tour_company = request.POST.get('tour_company', '')
            description = request.POST.get('description', '')
            tour_date = request.POST.get('tour_date')
            return_date = request.POST.get('return_date')
            
            # Get total cost directly
            total_cost = Decimal(request.POST.get('total_cost', 0))
            
            # Other details
            max_participants = int(request.POST.get('max_participants', 0))
            status = request.POST.get('status', 'Planned')
            
            # Validation
            if not name or not destination or not tour_date or not return_date:
                messages.error(request, 'Please fill in all required fields.')
                return redirect('tours:create_tour')
            
            if total_cost <= 0:
                messages.error(request, 'Total cost must be greater than zero.')
                return redirect('tours:create_tour')
            
            # Create tour
            tour = EducationalTour.objects.create(
                name=name,
                destination=destination,
                tour_company=tour_company,
                description=description,
                tour_date=tour_date,
                return_date=return_date,
                total_cost=total_cost,
                transportation_fee=0,
                accommodation_fee=0,
                food_allowance=0,
                entrance_fees=0,
                other_fees=0,
                max_participants=max_participants,
                status=status,
            )
            
            messages.success(request, f'Tour "{tour.name}" created successfully!')
            return redirect('tours:tour_list')
            
        except Exception as e:
            messages.error(request, f'Error creating tour: {str(e)}')
            return redirect('tours:create_tour')
    
    # Get existing tour companies for autocomplete
    existing_companies = EducationalTour.objects.exclude(
        tour_company__isnull=True
    ).exclude(
        tour_company=''
    ).values_list('tour_company', flat=True).distinct().order_by('tour_company')
    
    context = {
        'existing_companies': list(existing_companies)
    }
    return render(request, 'tours/create_tour.html', context)


@login_required
def edit_tour(request, tour_id):
    """Edit an existing tour"""
    tour = get_object_or_404(EducationalTour, id=tour_id)
    
    if request.method == 'POST':
        try:
            # Update tour data
            tour.name = request.POST.get('name')
            tour.destination = request.POST.get('destination')
            tour.tour_company = request.POST.get('tour_company', '')
            tour.description = request.POST.get('description', '')
            tour.tour_date = request.POST.get('tour_date')
            tour.return_date = request.POST.get('return_date')
            
            # Get total cost directly
            tour.total_cost = Decimal(request.POST.get('total_cost', 0))
            
            # Reset breakdown fields to 0
            tour.transportation_fee = 0
            tour.accommodation_fee = 0
            tour.food_allowance = 0
            tour.entrance_fees = 0
            tour.other_fees = 0
            
            tour.max_participants = int(request.POST.get('max_participants', 0))
            tour.status = request.POST.get('status', 'Planned')
            
            tour.save()
            
            messages.success(request, f'Tour "{tour.name}" updated successfully!')
            return redirect('tours:tour_list')
            
        except Exception as e:
            messages.error(request, f'Error updating tour: {str(e)}')
            return redirect('tours:edit_tour', tour_id=tour.id)
    
    # Get existing tour companies for autocomplete
    existing_companies = EducationalTour.objects.exclude(
        tour_company__isnull=True
    ).exclude(
        tour_company=''
    ).values_list('tour_company', flat=True).distinct().order_by('tour_company')
    
    context = {
        'tour': tour,
        'is_edit': True,
        'existing_companies': list(existing_companies)
    }
    return render(request, 'tours/create_tour.html', context)


@login_required
def delete_tour(request, tour_id):
    """Delete a tour"""
    tour = get_object_or_404(EducationalTour, id=tour_id)
    
    # Check if tour has enrollments
    if tour.enrollments.exists():
        messages.error(request, f'Cannot delete "{tour.name}" - it has student enrollments.')
        return redirect('tours:tour_list')
    
    tour_name = tour.name
    tour.delete()
    messages.success(request, f'Tour "{tour_name}" deleted successfully!')
    return redirect('tours:tour_list')


@login_required
def tour_list(request):
    """List all tours"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    tours = EducationalTour.objects.all()
    
    if status_filter:
        tours = tours.filter(status=status_filter)
    
    if search_query:
        tours = tours.filter(
            Q(name__icontains=search_query) |
            Q(destination__icontains=search_query) |
            Q(tour_company__icontains=search_query)
        )
    
    tours = tours.order_by('-tour_date')
    
    # Calculate progress for each tour
    tours_with_progress = []
    for tour in tours:
        total_participants = tour.get_total_participants()
        if total_participants > 0:
            expected_total = tour.total_cost * total_participants
            progress = (tour.get_total_paid() / expected_total * 100) if expected_total > 0 else 0
        else:
            progress = 0
        
        tour.progress_percentage = int(progress)
        tours_with_progress.append(tour)
    
    context = {
        'tours': tours_with_progress,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'tours/tour_list.html', context)
    # Get filters
    level_filter = request.GET.get('level', '')
    track_filter = request.GET.get('track', '')
    section_filter = request.GET.get('section', '')
    student_type = request.GET.get('type', 'all')
    
    # Get active tours - FIXED: Changed Tour to EducationalTour
    tours = EducationalTour.objects.filter(status='Planned').order_by('tour_date')
    
    # Get eligible students (adjust based on your model)
    students = Student.objects.filter(
        # Add your filtering logic here
    )
    
    # Apply filters
    if level_filter:
        students = students.filter(level_type=level_filter)  # Changed 'level' to 'level_type' to match your model
    if track_filter:
        students = students.filter(track_strand=track_filter)
    if section_filter:
        students = students.filter(section=section_filter)
    
    # Group by section
    sections = {}
    for student in students:
        section = student.section or 'No Section'
        if section not in sections:
            sections[section] = {
                'students': [],
                'track': student.track_strand,
                'type': 'Regular' if student.current_grade_level == 'Grade 11' else 'Payee'
            }
        sections[section]['students'].append(student)
    
    context = {
        'tours': tours,
        'sections': sections,
        'level_filter': level_filter,
        'track_filter': track_filter,
        'section_filter': section_filter,
        'student_type': student_type,
        'tracks': students.values_list('track_strand', flat=True).distinct(),
        'available_sections': students.values_list('section', flat=True).distinct(),
    }
    
    return render(request, 'tours/enrollment_management.html', context)


@login_required
def bulk_enroll_students_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tour_id = data.get('tour_id')
            student_ids = data.get('student_ids', [])
            
            # FIXED: Changed Tour to EducationalTour
            tour = EducationalTour.objects.get(id=tour_id)
            enrolled_count = 0
            
            for student_id in student_ids:
                student = Student.objects.get(id=student_id)
                # Check if already enrolled
                if not TourEnrollment.objects.filter(tour=tour, student=student).exists():
                    TourEnrollment.objects.create(
                        tour=tour,
                        student=student,
                        total_fee=tour.total_cost,
                        balance=tour.total_cost,
                        status='Enrolled'
                    )
                    enrolled_count += 1
            
            return JsonResponse({
                'success': True,
                'enrolled_count': enrolled_count,
                'message': f'Successfully enrolled {enrolled_count} students!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)