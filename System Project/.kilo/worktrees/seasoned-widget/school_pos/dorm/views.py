from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from datetime import datetime
from decimal import Decimal
from .models import DormBuilding, DormRoom, DormAssignment, DormPayment
from students.models import Student

def dorm_dashboard(request):
    """Main dashboard showing all dorm assignments"""
    # Get filter parameters
    building_filter = request.GET.get('building', '')
    gender_filter = request.GET.get('gender', '')
    
    # Get all active assignments
    assignments = DormAssignment.objects.filter(status='Active').select_related(
        'student', 'room', 'room__building'
    )
    
    # Apply filters
    if building_filter:
        assignments = assignments.filter(room__building_id=building_filter)
    if gender_filter:
        if hasattr(DormBuilding, 'gender_restriction'):
            assignments = assignments.filter(room__building__gender_restriction=gender_filter)
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        assignments = assignments.filter(
            Q(student__first_name__icontains=search) |
            Q(student__last_name__icontains=search) |
            Q(student__student_id__icontains=search) |
            Q(room__room_number__icontains=search)
        )
    
    # Statistics - OPTIMIZED
    total_students = DormAssignment.objects.filter(status='Active').count()
    total_rooms = DormRoom.objects.filter(is_active=True).count() if hasattr(DormRoom, 'is_active') else DormRoom.objects.count()
    occupied_rooms = DormRoom.objects.filter(
        assignments__status='Active'
    ).distinct().count()
    available_rooms = total_rooms - occupied_rooms
    
    # Get all buildings for filter
    buildings = DormBuilding.objects.all()
    if hasattr(DormBuilding, 'is_active'):
        buildings = buildings.filter(is_active=True)
    
    # Gender-specific stats - OPTIMIZED with database queries
    boys_count = DormAssignment.objects.filter(status='Active', student__gender='Male').count()
    girls_count = DormAssignment.objects.filter(status='Active', student__gender='Female').count()
    
    context = {
        'assignments': assignments,
        'total_students': total_students,
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'available_rooms': available_rooms,
        'boys_count': boys_count,
        'girls_count': girls_count,
        'buildings': buildings,
        'search': search,
        'building_filter': building_filter,
        'gender_filter': gender_filter,
    }
    return render(request, 'dorm/dashboard.html', context)


def add_dorm_assignment(request):
    """Add a new student to a dorm room with gender validation"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        room_id = request.POST.get('room_id')
        date_started = request.POST.get('date_started')
        notes = request.POST.get('notes', '')
        
        try:
            student = Student.objects.get(id=student_id)
            room = DormRoom.objects.get(id=room_id)
            
            # Check gender restriction
            if hasattr(room.building, 'gender_restriction') and room.building.gender_restriction != 'Mixed':
                if hasattr(student, 'gender') and student.gender and room.building.gender_restriction != student.gender:
                    messages.error(
                        request, 
                        f'❌ Gender mismatch! This building is for {room.building.get_gender_restriction_display()} only. '
                        f'Student gender: {student.gender}'
                    )
                    return redirect('dorm:add_assignment')
            
            # Check if room has capacity
            if not room.has_space():
                messages.error(request, '❌ Room is at full capacity!')
                return redirect('dorm:add_assignment')
            
            # Check if student already has active assignment
            if DormAssignment.objects.filter(student=student, status='Active').exists():
                messages.error(request, '❌ Student already has an active dorm assignment!')
                return redirect('dorm:add_assignment')
            
            # Create assignment
            assignment = DormAssignment.objects.create(
                student=student,
                room=room,
                date_started=date_started,
                notes=notes,
                status='Active'
            )
            
            messages.success(
                request, 
                f'✅ Successfully assigned {student} to {room}!'
            )
            return redirect('dorm:dorm_dashboard')
            
        except Student.DoesNotExist:
            messages.error(request, '❌ Student not found!')
        except DormRoom.DoesNotExist:
            messages.error(request, '❌ Room not found!')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
        
        return redirect('dorm:add_assignment')
    
    # GET request - show form
    students = Student.objects.all().order_by('last_name', 'first_name')
    buildings = DormBuilding.objects.filter(is_active=True).prefetch_related('rooms')
    
    context = {
        'students': students,
        'buildings': buildings,
    }
    return render(request, 'dorm/add_assignment.html', context)


def add_dorm_payment(request, assignment_id):
    """Record a payment for dorm fees"""
    assignment = get_object_or_404(DormAssignment, id=assignment_id)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            month_covered = request.POST.get('month_covered')
            year_covered = int(request.POST.get('year_covered', datetime.now().year))
            payment_method = request.POST.get('payment_method')
            remarks = request.POST.get('remarks', '')
            
            # Generate receipt number
            receipt_number = f"DORM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            payment = DormPayment.objects.create(
                assignment=assignment,
                amount=amount,
                month_covered=month_covered,
                year_covered=year_covered,
                payment_method=payment_method,
                receipt_number=receipt_number,
                remarks=remarks
            )
            
            messages.success(request, f'✅ Payment recorded! Receipt: {receipt_number}')
            return redirect('dorm:payment_receipt', payment_id=payment.id)
            
        except (ValueError, TypeError) as e:
            messages.error(request, f'❌ Invalid input: {str(e)}')
            return redirect('dorm:dorm_dashboard')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('dorm:dorm_dashboard')
    
    context = {
        'assignment': assignment,
    }
    return render(request, 'dorm/add_payment.html', context)


def payment_receipt(request, payment_id):
    """Display/Print payment receipt"""
    payment = get_object_or_404(DormPayment, id=payment_id)
    
    context = {
        'payment': payment,
    }
    return render(request, 'dorm/receipt.html', context)


def terminate_assignment(request, assignment_id):
    """End a dorm assignment"""
    assignment = get_object_or_404(DormAssignment, id=assignment_id)
    
    if request.method == 'POST':
        date_ended = request.POST.get('date_ended')
        assignment.date_ended = date_ended
        assignment.status = 'Completed'
        assignment.save()
        
        messages.success(request, f'✅ Assignment for {assignment.student} has been terminated.')
        return redirect('dorm:dorm_dashboard')
    
    context = {
        'assignment': assignment,
    }
    return render(request, 'dorm/terminate_assignment.html', context)


# ============================================================================
# BUILDING MANAGEMENT
# ============================================================================

def manage_buildings(request):
    """Manage dormitory buildings"""
    buildings = DormBuilding.objects.all().order_by('name')
    
    context = {
        'buildings': buildings,
    }
    return render(request, 'dorm/manage_buildings.html', context)


def add_building(request):
    """Add a new dormitory building"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            gender_restriction = request.POST.get('gender_restriction', 'Mixed')
            total_rooms = int(request.POST.get('total_rooms', 0))
            description = request.POST.get('description', '')
            
            if not name:
                messages.error(request, '❌ Building name is required!')
                return render(request, 'dorm/add_building.html')
            
            if total_rooms <= 0:
                messages.error(request, '❌ Total rooms must be greater than 0!')
                return render(request, 'dorm/add_building.html')
            
            building = DormBuilding.objects.create(
                name=name,
                gender_restriction=gender_restriction,
                total_rooms=total_rooms,
                description=description,
                is_active=True
            )
            messages.success(request, f'✅ Building "{name}" created successfully!')
            return redirect('dorm:manage_buildings')
            
        except ValueError:
            messages.error(request, '❌ Invalid number format for total rooms!')
            return render(request, 'dorm/add_building.html')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return render(request, 'dorm/add_building.html')
    
    return render(request, 'dorm/add_building.html')


def edit_building(request, building_id):
    """Edit an existing building"""
    building = get_object_or_404(DormBuilding, id=building_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            total_rooms = int(request.POST.get('total_rooms', building.total_rooms))
            
            if not name:
                messages.error(request, '❌ Building name is required!')
                return render(request, 'dorm/edit_building.html', {'building': building})
            
            building.name = name
            building.gender_restriction = request.POST.get('gender_restriction')
            building.total_rooms = total_rooms
            building.description = request.POST.get('description', '')
            building.is_active = 'is_active' in request.POST
            building.save()
            
            messages.success(request, f'✅ Building "{building.name}" updated!')
            return redirect('dorm:manage_buildings')
            
        except ValueError:
            messages.error(request, '❌ Invalid number format!')
            return render(request, 'dorm/edit_building.html', {'building': building})
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return render(request, 'dorm/edit_building.html', {'building': building})
    
    context = {
        'building': building,
    }
    return render(request, 'dorm/edit_building.html', context)


def delete_building(request, building_id):
    """Delete a building (soft delete)"""
    building = get_object_or_404(DormBuilding, id=building_id)
    
    if request.method == 'POST':
        # Check if building has active assignments
        active_count = DormAssignment.objects.filter(
            room__building=building,
            status='Active'
        ).count()
        
        if active_count > 0:
            messages.error(
                request, 
                f'❌ Cannot delete building with {active_count} active assignments!'
            )
        else:
            building.is_active = False
            building.save()
            messages.success(request, f'✅ Building "{building.name}" deactivated!')
        
        return redirect('dorm:manage_buildings')
    
    context = {
        'building': building,
    }
    return render(request, 'dorm/delete_building.html', context)


# ============================================================================
# ROOM MANAGEMENT
# ============================================================================

def manage_rooms(request, building_id=None):
    """Manage rooms in all or specific building"""
    if building_id:
        building = get_object_or_404(DormBuilding, id=building_id)
        rooms = building.rooms.all()
    else:
        building = None
        rooms = DormRoom.objects.all().select_related('building')
    
    buildings = DormBuilding.objects.filter(is_active=True)
    
    context = {
        'building': building,
        'rooms': rooms,
        'buildings': buildings,
    }
    return render(request, 'dorm/manage_rooms.html', context)


def add_room(request):
    """Add a new room"""
    if request.method == 'POST':
        try:
            building_id = request.POST.get('building_id')
            room_number = request.POST.get('room_number', '').strip()
            room_type = request.POST.get('room_type')
            capacity = int(request.POST.get('capacity', 1))
            monthly_rate = Decimal(request.POST.get('monthly_rate', '0'))
            description = request.POST.get('description', '')
            
            if not building_id:
                messages.error(request, '❌ Please select a building!')
                return render(request, 'dorm/add_room.html', {'buildings': DormBuilding.objects.filter(is_active=True)})
            
            if not room_number:
                messages.error(request, '❌ Room number is required!')
                return render(request, 'dorm/add_room.html', {'buildings': DormBuilding.objects.filter(is_active=True)})
            
            if capacity <= 0:
                messages.error(request, '❌ Capacity must be greater than 0!')
                return render(request, 'dorm/add_room.html', {'buildings': DormBuilding.objects.filter(is_active=True)})
            
            if monthly_rate <= 0:
                messages.error(request, '❌ Monthly rate must be greater than 0!')
                return render(request, 'dorm/add_room.html', {'buildings': DormBuilding.objects.filter(is_active=True)})
            
            building = DormBuilding.objects.get(id=building_id)
            room = DormRoom.objects.create(
                building=building,
                room_number=room_number,
                room_type=room_type,
                capacity=capacity,
                monthly_rate=monthly_rate,
                description=description,
                is_available=True,
                is_active=True
            )
            messages.success(request, f'✅ Room {room_number} created in {building.name}!')
            return redirect('dorm:manage_rooms')
            
        except DormBuilding.DoesNotExist:
            messages.error(request, '❌ Building not found!')
        except ValueError:
            messages.error(request, '❌ Invalid number format!')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
    
    buildings = DormBuilding.objects.filter(is_active=True)
    context = {
        'buildings': buildings,
    }
    return render(request, 'dorm/add_room.html', context)


def edit_room(request, room_id):
    """Edit an existing room"""
    room = get_object_or_404(DormRoom, id=room_id)
    
    if request.method == 'POST':
        try:
            room_number = request.POST.get('room_number', '').strip()
            capacity = int(request.POST.get('capacity', room.capacity))
            monthly_rate = Decimal(request.POST.get('monthly_rate', room.monthly_rate))
            
            if not room_number:
                messages.error(request, '❌ Room number is required!')
                return render(request, 'dorm/edit_room.html', {'room': room})
            
            room.room_number = room_number
            room.room_type = request.POST.get('room_type')
            room.capacity = capacity
            room.monthly_rate = monthly_rate
            room.description = request.POST.get('description', '')
            room.is_available = 'is_available' in request.POST
            room.is_active = 'is_active' in request.POST
            room.save()
            
            messages.success(request, f'✅ Room {room.room_number} updated!')
            return redirect('dorm:manage_rooms')
            
        except ValueError:
            messages.error(request, '❌ Invalid number format!')
            return render(request, 'dorm/edit_room.html', {'room': room})
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return render(request, 'dorm/edit_room.html', {'room': room})
    
    context = {
        'room': room,
    }
    return render(request, 'dorm/edit_room.html', context)


def delete_room(request, room_id):
    """Delete a room (soft delete)"""
    room = get_object_or_404(DormRoom, id=room_id)
    
    if request.method == 'POST':
        # Check if room has active assignments
        active_count = room.assignments.filter(status='Active').count()
        
        if active_count > 0:
            messages.error(
                request, 
                f'❌ Cannot delete room with {active_count} active assignments!'
            )
        else:
            room.is_active = False
            room.save()
            messages.success(request, f'✅ Room {room.room_number} deactivated!')
        
        return redirect('dorm:manage_rooms')
    
    context = {
        'room': room,
    }
    return render(request, 'dorm/delete_room.html', context)