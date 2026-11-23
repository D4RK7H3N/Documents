"""
Staff views for authentication and dashboard
File: staff/views.py
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import StaffRegisterForm, StaffLoginForm
from django.contrib.admin.views.decorators import staff_member_required


def staff_home(request):
    """Redirect staff root URL to dashboard if logged in, else login page."""
    if not request.user.is_authenticated:
        return redirect("staff:staff_login")
    
    if request.user.is_staff and not request.user.is_superuser:
        return redirect("staff:staff_dashboard")
    
    return redirect("staff:staff_login")


def home(request):
    """Main home view - redirects based on user authentication."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('staff:staff_dashboard')
    return redirect('staff:staff_login')


@staff_member_required
def staff_register(request):
    """Register new staff users (admin only)."""
    if not request.user.is_superuser:
        messages.error(request, "Only administrators can create staff accounts.")
        return redirect('admin:index')
    
    if request.method == 'POST':
        form = StaffRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            user.is_superuser = False
            user.save()
            messages.success(request, f'Staff account for {user.username} created successfully!')
            return redirect('admin:auth_user_changelist')
    else:
        form = StaffRegisterForm()
    
    return render(request, 'staff/register.html', {'form': form})


def staff_login(request):
    """
    Staff login view with case-insensitive authentication.
    Works with CaseInsensitiveAuthBackend in settings.
    """
    # Already logged in?
    if request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser:
        return redirect('staff:staff_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            messages.error(request, "Please enter both username and password.")
            return render(request, 'staff/login.html')
        
        # Authenticate user (case-insensitive via authentication backend)
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is staff (not superuser)
            if user.is_staff and not user.is_superuser:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('staff:staff_dashboard')
            elif user.is_superuser:
                messages.error(request, "Please use the admin panel to login.")
            else:
                messages.error(request, "You are not authorized as staff.")
        else:
            messages.error(request, "Invalid username or password. Please try again.")
        
        return render(request, 'staff/login.html')
    
    else:
        # GET request - show login form
        return render(request, 'staff/login.html')


@login_required(login_url='staff:staff_login')
def staff_dashboard(request):
    """Staff dashboard - only accessible to authenticated staff members."""
    if not request.user.is_staff or request.user.is_superuser:
        logout(request)
        messages.error(request, 'Invalid access. Please login as staff.')
        return redirect('staff:staff_login')
    
    context = {
        'user': request.user,
    }
    return render(request, 'staff/dashboard.html', context)


def staff_logout(request):
    """Staff logout view."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('staff:staff_login')