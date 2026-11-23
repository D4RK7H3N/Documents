from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum
from decimal import Decimal, DecimalException
from django.utils import timezone
from students.models import Student
from .models import GraduationEvent, StudentGraduation, GraduationPayment

# Explicitly import StudentEnrollment if it exists in students app
try:
    from students.models import StudentEnrollment
except ImportError:
    StudentEnrollment = None

# Use the same decorator pattern as other apps
try:
    from school_pos.decorators import staff_required
    require_staff = staff_required
except ImportError:
    require_staff = login_required

try:
    from school_pos.decorators import admin_required
    require_admin = admin_required
except ImportError:
    require_admin = login_required


@require_staff
def graduation_dashboard(request):
    """Main dashboard for graduation events"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    # Get all graduation events
    events = GraduationEvent.objects.all()

    # Apply filters
    if search_query:
        events = events.filter(
            Q(name__icontains=search_query) |
            Q(venue__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if status_filter:
        events = events.filter(status=status_filter)

    # Get summary statistics
    total_events = events.count()
    active_events = events.filter(status='Registration').count()
    total_participants = sum(event.get_total_participants() for event in events)
    total_revenue = sum(event.get_total_paid() for event in events)

    context = {
        'events': events,
        'total_events': total_events,
        'active_events': active_events,
        'total_participants': total_participants,
        'total_revenue': total_revenue,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': GraduationEvent.STATUS_CHOICES,
    }
    return render(request, 'graduation/dashboard.html', context)


@require_staff
def graduation_event_detail(request, event_id):
    """Detail view for a specific graduation event"""
    event = get_object_or_404(GraduationEvent, id=event_id)

    # Get participants
    participants = event.participants.select_related('student').all()

    # Apply filters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    level_filter = request.GET.get('level', '')

    if search_query:
        participants = participants.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__lrn__icontains=search_query)
        )

    if status_filter:
        participants = participants.filter(status=status_filter)

    if level_filter:
        participants = participants.filter(graduation_level=level_filter)

    # Get summary stats
    total_registered = participants.filter(status__in=['Registered', 'Partial', 'Paid']).count()
    fully_paid = participants.filter(status='Paid').count()
    partial_paid = participants.filter(status='Partial').count()
    total_expected = event.total_fee_per_student * total_registered

    context = {
        'event': event,
        'participants': participants,
        'total_registered': total_registered,
        'fully_paid': fully_paid,
        'partial_paid': partial_paid,
        'total_expected': total_expected,
        'search_query': search_query,
        'status_filter': status_filter,
        'level_filter': level_filter,
        'level_choices': StudentGraduation.GRADUATION_LEVEL_CHOICES,
        'status_choices': StudentGraduation.STATUS_CHOICES,
    }
    return render(request, 'graduation/event_detail.html', context)


@require_staff
def register_student(request, event_id):
    """Register a student for graduation event"""
    event = get_object_or_404(GraduationEvent, id=event_id)

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        graduation_level = request.POST.get('graduation_level')
        section = request.POST.get('section', '')

        student = get_object_or_404(Student, id=student_id)

        # Check if already registered
        if StudentGraduation.objects.filter(graduation_event=event, student=student).exists():
            messages.error(request, f'{student.first_name} {student.last_name} is already registered for this event.')
            return redirect('graduation:event_detail', event_id=event_id)

        # Check if registration is open
        if not event.is_registration_open():
            messages.error(request, 'Registration is closed for this event.')
            return redirect('graduation:event_detail', event_id=event_id)

        # Check if slots are available
        if event.max_participants > 0 and event.get_total_participants() >= event.max_participants:
            messages.error(request, 'This event has reached maximum capacity.')
            return redirect('graduation:event_detail', event_id=event_id)

        # Create registration
        student_graduation = StudentGraduation.objects.create(
            graduation_event=event,
            student=student,
            graduation_level=graduation_level,
            section=section,
            total_fee=event.total_fee_per_student
        )

        messages.success(request, f'Successfully registered {student.first_name} {student.last_name} for {event.name}.')
        return redirect('graduation:event_detail', event_id=event_id)

    # GET request - show student selection form
    # Get students not already registered for this event
    registered_student_ids = event.participants.values_list('student_id', flat=True)
    available_students = Student.objects.exclude(id__in=registered_student_ids)

    return render(request, 'graduation/register_student.html', {
        'event': event,
        'students': available_students,
        'level_choices': StudentGraduation.GRADUATION_LEVEL_CHOICES,
    })


@require_staff
def payment(request, student_graduation_id):
    """Process payment for graduation"""
    student_graduation = get_object_or_404(
        StudentGraduation.objects.select_related('student', 'graduation_event'),
        id=student_graduation_id
    )

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount') or 0)
            method = request.POST.get('method')
            reference = request.POST.get('reference', '')
            gcash_number = request.POST.get('gcash_number', '')
            remarks = request.POST.get('remarks', '')

            if amount <= 0:
                messages.error(request, 'Payment amount must be greater than zero.')
                return redirect('graduation:payment', student_graduation_id=student_graduation_id)

            if amount > student_graduation.balance:
                messages.error(request, f'Payment amount cannot exceed the balance of ₱{student_graduation.balance:,.2f}.')
                return redirect('graduation:payment', student_graduation_id=student_graduation_id)

            # Create payment record
            GraduationPayment.objects.create(
                student_graduation=student_graduation,
                graduation_event=student_graduation.graduation_event,
                student=student_graduation.student,
                amount=amount,
                method=method,
                reference_number=reference,
                gcash_number=gcash_number,
                received_by=request.user.username,
                remarks=remarks
            )

            messages.success(
                request,
                f'Payment of ₱{amount:,.2f} received successfully for {student_graduation.student.first_name} {student_graduation.student.last_name}.'
            )
            return redirect('graduation:student_detail', student_graduation_id=student_graduation_id)

        except (ValueError, DecimalException):
            messages.error(request, 'Invalid amount format.')
            return redirect('graduation:payment', student_graduation_id=student_graduation_id)

    # GET request - show payment form
    payments = student_graduation.get_payment_history()

    return render(request, 'graduation/payment.html', {
        'student_graduation': student_graduation,
        'payments': payments,
        'payment_methods': GraduationPayment.PAYMENT_METHOD_CHOICES,
    })


@require_staff
def student_detail(request, student_graduation_id):
    """Detail view for a student's graduation record"""
    student_graduation = get_object_or_404(
        StudentGraduation.objects.select_related('student', 'graduation_event'),
        id=student_graduation_id
    )

    payments = student_graduation.get_payment_history()

    context = {
        'student_graduation': student_graduation,
        'payments': payments,
        'progress': student_graduation.get_payment_progress(),
    }
    return render(request, 'graduation/student_detail.html', context)


@require_admin
def create_event(request):
    """Create a new graduation event"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            event_date = request.POST.get('event_date')
            registration_deadline = request.POST.get('registration_deadline')

            # Fee structure
            base_fee = Decimal(request.POST.get('base_fee') or 0)
            gown_fee = Decimal(request.POST.get('gown_fee') or 0)
            diploma_fee = Decimal(request.POST.get('diploma_fee') or 0)
            ceremony_fee = Decimal(request.POST.get('ceremony_fee') or 0)
            yearbook_fee = Decimal(request.POST.get('yearbook_fee') or 0)
            other_fees = Decimal(request.POST.get('other_fees') or 0)

            # Event details
            venue = request.POST.get('venue', '')
            time = request.POST.get('time')
            max_participants = int(request.POST.get('max_participants') or 0)

            # Create event
            event = GraduationEvent.objects.create(
                name=name,
                description=description,
                event_date=event_date,
                registration_deadline=registration_deadline,
                base_fee=base_fee,
                gown_fee=gown_fee,
                diploma_fee=diploma_fee,
                ceremony_fee=ceremony_fee,
                yearbook_fee=yearbook_fee,
                other_fees=other_fees,
                venue=venue,
                time=time,
                max_participants=max_participants,
            )

            messages.success(request, f'Graduation event "{name}" created successfully.')
            return redirect('graduation:event_detail', event_id=event.id)

        except Exception as e:
            messages.error(request, f'Error creating event: {str(e)}')
            return redirect('graduation:create_event')

    # GET request - show create form
    status_choices = GraduationEvent.STATUS_CHOICES
    return render(request, 'graduation/create_event.html', {
        'status_choices': status_choices,
    })


@require_admin
def edit_event(request, event_id):
    """Edit graduation event"""
    event = get_object_or_404(GraduationEvent, id=event_id)

    if request.method == 'POST':
        try:
            # Update event
            event.name = request.POST.get('name')
            event.description = request.POST.get('description', '')
            event.event_date = request.POST.get('event_date')
            event.registration_deadline = request.POST.get('registration_deadline')

            # Fee structure
            event.base_fee = Decimal(request.POST.get('base_fee') or 0)
            event.gown_fee = Decimal(request.POST.get('gown_fee') or 0)
            event.diploma_fee = Decimal(request.POST.get('diploma_fee') or 0)
            event.ceremony_fee = Decimal(request.POST.get('ceremony_fee') or 0)
            event.yearbook_fee = Decimal(request.POST.get('yearbook_fee') or 0)
            event.other_fees = Decimal(request.POST.get('other_fees') or 0)

            # Event details
            event.venue = request.POST.get('venue', '')
            event.time = request.POST.get('time')
            event.max_participants = int(request.POST.get('max_participants') or 0)

            event.save()

            messages.success(request, f'Event "{event.name}" updated successfully.')
            return redirect('graduation:event_detail', event_id=event.id)

        except Exception as e:
            messages.error(request, f'Error updating event: {str(e)}')

    # GET request - show edit form
    return render(request, 'graduation/edit_event.html', {
        'event': event,
        'status_choices': GraduationEvent.STATUS_CHOICES,
    })


@require_admin
def delete_registration(request, student_graduation_id):
    """Delete/cancel student registration"""
    student_graduation = get_object_or_404(StudentGraduation, id=student_graduation_id)

    if request.method == 'POST':
        event_id = student_graduation.graduation_event.id
        student_name = f"{student_graduation.student.first_name} {student_graduation.student.last_name}"

        # Check if there are payments
        if student_graduation.amount_paid > 0:
            messages.error(
                request,
                f'Cannot delete registration for {student_name} because payments have been made. Refund payments first.'
            )
        else:
            student_graduation.delete()
            messages.success(request, f'Registration for {student_name} has been cancelled.')

        return redirect('graduation:event_detail', event_id=event_id)

    return render(request, 'graduation/delete_registration.html', {
        'student_graduation': student_graduation
    })


@login_required
def graduation_dashboard(request):
    """Main dashboard for graduation events"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    level_filter = request.GET.get('level', '')

    # Get all graduation events
    events = GraduationEvent.objects.all()

    # Apply filters
    if search_query:
        events = events.filter(
            Q(name__icontains=search_query) |
            Q(venue__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if status_filter:
        events = events.filter(status=status_filter)

    # Get summary statistics
    total_events = events.count()
    active_events = events.filter(status='Registration').count()
    total_participants = sum(event.get_total_participants() for event in events)
    total_revenue = sum(event.get_total_paid() for event in events)

    context = {
        'events': events,
        'total_events': total_events,
        'active_events': active_events,
        'total_participants': total_participants,
        'total_revenue': total_revenue,
        'search_query': search_query,
        'status_filter': status_filter,
        'level_filter': level_filter,
    }
    return render(request, 'graduation/dashboard.html', context)


@login_required
def graduation_event_detail(request, event_id):
    """Detail view for a specific graduation event"""
    event = get_object_or_404(GraduationEvent, id=event_id)

    # Get participants
    participants = event.participants.select_related('student').all()

    # Apply filters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    level_filter = request.GET.get('level', '')

    if search_query:
        participants = participants.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__lrn__icontains=search_query)
        )

    if status_filter:
        participants = participants.filter(status=status_filter)

    if level_filter:
        participants = participants.filter(graduation_level=level_filter)

    # Get summary stats
    total_registered = participants.filter(status__in=['Registered', 'Partial', 'Paid']).count()
    fully_paid = participants.filter(status='Paid').count()
    partial_paid = participants.filter(status='Partial').count()
    total_expected = event.total_fee_per_student * total_registered
    total_paid = Sum('amount_paid')

    context = {
        'event': event,
        'participants': participants,
        'total_registered': total_registered,
        'fully_paid': fully_paid,
        'partial_paid': partial_paid,
        'total_expected': total_expected,
        'search_query': search_query,
        'status_filter': status_filter,
        'level_filter': level_filter,
    }
    return render(request, 'graduation/event_detail.html', context)


@login_required
def register_student(request, event_id):
    """Register a student for graduation event"""
    event = get_object_or_404(GraduationEvent, id=event_id)

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        graduation_level = request.POST.get('graduation_level')
        section = request.POST.get('section')

        student = get_object_or_404(Student, id=student_id)

        # Check if already registered
        if StudentGraduation.objects.filter(graduation_event=event, student=student).exists():
            messages.error(request, f'{student.first_name} {student.last_name} is already registered for this event.')
            return redirect('graduation:event_detail', event_id=event_id)

        # Check if registration is open
        if not event.is_registration_open():
            messages.error(request, 'Registration is closed for this event.')
            return redirect('graduation:event_detail', event_id=event_id)

        # Check if slots are available
        if event.max_participants > 0 and event.get_total_participants() >= event.max_participants:
            messages.error(request, 'This event has reached maximum capacity.')
            return redirect('graduation:event_detail', event_id=event_id)

        # Create registration
        student_graduation = StudentGraduation.objects.create(
            graduation_event=event,
            student=student,
            graduation_level=graduation_level,
            section=section,
            total_fee=event.total_fee_per_student
        )

        messages.success(request, f'Successfully registered {student.first_name} {student.last_name} for {event.name}.')
        return redirect('graduation:event_detail', event_id=event_id)

    # GET request - show student selection form
    # Get students not already registered for this event
    registered_student_ids = event.participants.values_list('student_id', flat=True)
    available_students = Student.objects.exclude(id__in=registered_student_ids)

    return render(request, 'graduation/register_student.html', {
        'event': event,
        'students': available_students
    })


@login_required
def payment(request, student_graduation_id):
    """Process payment for graduation"""
    student_graduation = get_object_or_404(
        StudentGraduation.objects.select_related('student', 'graduation_event'),
        id=student_graduation_id
    )

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount') or 0)
            method = request.POST.get('method')
            reference = request.POST.get('reference', '')
            gcash_number = request.POST.get('gcash_number', '')
            remarks = request.POST.get('remarks', '')

            if amount <= 0:
                messages.error(request, 'Payment amount must be greater than zero.')
                return redirect('graduation:payment', student_graduation_id=student_graduation_id)

            if amount > student_graduation.balance:
                messages.error(request, f'Payment amount cannot exceed the balance of ₱{student_graduation.balance:,.2f}.')
                return redirect('graduation:payment', student_graduation_id=student_graduation_id)

            # Create payment record
            GraduationPayment.objects.create(
                student_graduation=student_graduation,
                graduation_event=student_graduation.graduation_event,
                student=student_graduation.student,
                amount=amount,
                method=method,
                reference_number=reference,
                gcash_number=gcash_number,
                received_by=request.user.username,
                remarks=remarks
            )

            messages.success(
                request,
                f'Payment of ₱{amount:,.2f} received successfully for {student_graduation.student.first_name} {student_graduation.student.last_name}.'
            )
            return redirect('graduation:student_detail', student_graduation_id=student_graduation_id)

        except (ValueError, DecimalException):
            messages.error(request, 'Invalid amount format.')
            return redirect('graduation:payment', student_graduation_id=student_graduation_id)

    # GET request - show payment form
    payments = student_graduation.get_payment_history()

    return render(request, 'graduation/payment.html', {
        'student_graduation': student_graduation,
        'payments': payments,
        'payment_methods': GraduationPayment.PAYMENT_METHOD_CHOICES,
    })


@login_required
def student_detail(request, student_graduation_id):
    """Detail view for a student's graduation record"""
    student_graduation = get_object_or_404(
        StudentGraduation.objects.select_related('student', 'graduation_event'),
        id=student_graduation_id
    )

    payments = student_graduation.get_payment_history()

    context = {
        'student_graduation': student_graduation,
        'payments': payments,
        'progress': student_graduation.get_payment_progress(),
    }
    return render(request, 'graduation/student_detail.html', context)


@login_required
def create_event(request):
    """Create a new graduation event"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            event_date = request.POST.get('event_date')
            registration_deadline = request.POST.get('registration_deadline')

            # Fee structure
            base_fee = Decimal(request.POST.get('base_fee') or 0)
            gown_fee = Decimal(request.POST.get('gown_fee') or 0)
            diploma_fee = Decimal(request.POST.get('diploma_fee') or 0)
            ceremony_fee = Decimal(request.POST.get('ceremony_fee') or 0)
            yearbook_fee = Decimal(request.POST.get('yearbook_fee') or 0)
            other_fees = Decimal(request.POST.get('other_fees') or 0)

            # Event details
            venue = request.POST.get('venue', '')
            time = request.POST.get('time')
            max_participants = int(request.POST.get('max_participants') or 0)

            # Create event
            event = GraduationEvent.objects.create(
                name=name,
                description=description,
                event_date=event_date,
                registration_deadline=registration_deadline,
                base_fee=base_fee,
                gown_fee=gown_fee,
                diploma_fee=diploma_fee,
                ceremony_fee=ceremony_fee,
                yearbook_fee=yearbook_fee,
                other_fees=other_fees,
                venue=venue,
                time=time,
                max_participants=max_participants,
            )

            messages.success(request, f'Graduation event "{name}" created successfully.')
            return redirect('graduation:event_detail', event_id=event.id)

        except Exception as e:
            messages.error(request, f'Error creating event: {str(e)}')
            return redirect('graduation:create_event')

    # GET request - show create form
    return render(request, 'graduation/create_event.html')


@login_required
def edit_event(request, event_id):
    """Edit graduation event"""
    event = get_object_or_404(GraduationEvent, id=event_id)

    if request.method == 'POST':
        try:
            # Update event
            event.name = request.POST.get('name')
            event.description = request.POST.get('description', '')
            event.event_date = request.POST.get('event_date')
            event.registration_deadline = request.POST.get('registration_deadline')

            # Fee structure
            event.base_fee = Decimal(request.POST.get('base_fee') or 0)
            event.gown_fee = Decimal(request.POST.get('gown_fee') or 0)
            event.diploma_fee = Decimal(request.POST.get('diploma_fee') or 0)
            event.ceremony_fee = Decimal(request.POST.get('ceremony_fee') or 0)
            event.yearbook_fee = Decimal(request.POST.get('yearbook_fee') or 0)
            event.other_fees = Decimal(request.POST.get('other_fees') or 0)

            # Event details
            event.venue = request.POST.get('venue', '')
            event.time = request.POST.get('time')
            event.max_participants = int(request.POST.get('max_participants') or 0)

            event.save()

            messages.success(request, f'Event "{event.name}" updated successfully.')
            return redirect('graduation:event_detail', event_id=event.id)

        except Exception as e:
            messages.error(request, f'Error updating event: {str(e)}')

    # GET request - show edit form
    return render(request, 'graduation/edit_event.html', {'event': event})


@login_required
def delete_registration(request, student_graduation_id):
    """Delete/cancel student registration"""
    student_graduation = get_object_or_404(StudentGraduation, id=student_graduation_id)

    if request.method == 'POST':
        event_id = student_graduation.graduation_event.id
        student_name = f"{student_graduation.student.first_name} {student_graduation.student.last_name}"

        # Check if there are payments
        if student_graduation.amount_paid > 0:
            messages.error(
                request,
                f'Cannot delete registration for {student_name} because payments have been made. Refund payments first.'
            )
        else:
            student_graduation.delete()
            messages.success(request, f'Registration for {student_name} has been cancelled.')

        return redirect('graduation:event_detail', event_id=event_id)

    return render(request, 'graduation/delete_registration.html', {
        'student_graduation': student_graduation
    })


@require_staff
def students_with_balance(request):
    """List all students who have outstanding graduation fees"""
    search_query = request.GET.get('search', '')
    level_filter = request.GET.get('level', '')
    event_filter = request.GET.get('event', '')

    # Get all student graduations with outstanding balance
    students_with_balance = StudentGraduation.objects.select_related(
        'student', 'graduation_event'
    ).filter(
        balance__gt=0
    ).exclude(
        status='Cancelled'
    )

    # Apply filters
    if search_query:
        students_with_balance = students_with_balance.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__lrn__icontains=search_query)
        )

    if level_filter:
        students_with_balance = students_with_balance.filter(graduation_level=level_filter)

    if event_filter:
        students_with_balance = students_with_balance.filter(graduation_event_id=event_filter)

    # Get summary statistics
    total_students = students_with_balance.count()
    total_balance = students_with_balance.aggregate(Sum('balance'))['balance__sum'] or 0

    # Group by event for summary
    events_summary = students_with_balance.values(
        'graduation_event__name',
        'graduation_event__id'
    ).annotate(
        student_count=Count('id'),
        total_balance=Sum('balance')
    ).order_by('-total_balance')

    context = {
        'students': students_with_balance,
        'total_students': total_students,
        'total_balance': total_balance,
        'events_summary': events_summary,
        'search_query': search_query,
        'level_filter': level_filter,
        'event_filter': event_filter,
        'level_choices': StudentGraduation.GRADUATION_LEVEL_CHOICES,
        'events': GraduationEvent.objects.filter(status__in=['Registration', 'Closed']),
    }
    return render(request, 'graduation/students_with_balance.html', context)


@require_staff
def graduation_summary_report(request):
    """Summary report of all graduation events and payments"""
    # Overall statistics
    total_events = GraduationEvent.objects.count()
    total_participants = StudentGraduation.objects.filter(
        status__in=['Registered', 'Partial', 'Paid']
    ).count()
    total_collected = GraduationPayment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_expected = sum(
        event.get_total_expected_revenue()
        for event in GraduationEvent.objects.all()
    )
    overall_balance = total_expected - total_collected

    # Event-wise breakdown
    event_summaries = []
    for event in GraduationEvent.objects.all().order_by('-event_date'):
        participants = event.get_total_participants()
        collected = event.get_total_paid()
        expected = event.get_total_expected_revenue()
        balance = event.get_total_balance()

        event_summaries.append({
            'event': event,
            'participants': participants,
            'collected': collected,
            'expected': expected,
            'balance': balance,
            'completion_rate': (collected / expected * 100) if expected > 0 else 0
        })

    context = {
        'total_events': total_events,
        'total_participants': total_participants,
        'total_collected': total_collected,
        'total_expected': total_expected,
        'overall_balance': overall_balance,
        'event_summaries': event_summaries,
    }
    return render(request, 'graduation/summary_report.html', context)
