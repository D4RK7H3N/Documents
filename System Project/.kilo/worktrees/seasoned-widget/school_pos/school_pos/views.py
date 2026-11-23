from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages, admin
from django.urls import path
from students.models import Student
from products.models import Product
from sales.models import Sale
from payments.models import Payment

def staff_login(request):
    """Custom login page for staff only."""
    if request.user.is_authenticated:
        return redirect("cashier:dashboard")  # Already logged in → cashier dashboard

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:  # Ensure staff-only login
            login(request, user)
            return redirect("cashier:dashboard")
        else:
            messages.error(request, "Invalid credentials or not authorized as staff.")

    return render(request, "staff_login.html")

def staff_logout(request):
    """Logout staff and redirect to login page."""
    logout(request)
    return redirect("staff_login")


class CustomAdminSite(admin.AdminSite):
    site_header = "School Administration"
    site_title = "School Admin"
    index_title = "Dashboard"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_view(self.custom_dashboard), name='index'),
        ]
        return custom_urls + urls
    
    def custom_dashboard(self, request):
        """Custom dashboard with real data"""
        # Get counts
        student_count = Student.objects.count()
        product_count = Product.objects.count()
        sales_count = Sale.objects.count()
        payment_count = Payment.objects.count()
        
        # Get sales data by month (you can customize this with real queries)
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        from datetime import datetime, timedelta
        
        # Last 6 months sales data
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_sales = Sale.objects.filter(
            created_at__gte=six_months_ago
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        sales_labels = [sale['month'].strftime('%b') for sale in monthly_sales]
        sales_values = [sale['count'] for sale in monthly_sales]
        
        # If no data, use defaults
        if not sales_labels:
            sales_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
            sales_values = [0, 0, 0, 0, 0, 0]
        
        # Get payment methods data
        payment_methods = Payment.objects.values('payment_method').annotate(
            count=Count('id')
        ).order_by('-count')
        
        payment_labels = [p['payment_method'] for p in payment_methods]
        payment_values = [p['count'] for p in payment_methods]
        
        # If no data, use defaults
        if not payment_labels:
            payment_labels = ['Cash', 'GCash', 'Card', 'Bank']
            payment_values = [0, 0, 0, 0]
        
        context = {
            'student_count': student_count,
            'product_count': product_count,
            'sales_count': sales_count,
            'payment_count': payment_count,
            'sales_labels': sales_labels,
            'sales_values': sales_values,
            'payment_labels': payment_labels,
            'payment_values': payment_values,
            **self.each_context(request),
        }
        
        return render(request, 'admin/index.html', context)


# Create custom admin site instance 
admin_site = CustomAdminSite(name='custom_admin')


# from students.admin import StudentAdmin
# from products.admin import ProductAdmin
# from sales.admin import SaleAdmin
# from payments.admin import PaymentAdmin

# admin_site.register(Student, StudentAdmin)
# admin_site.register(Product, ProductAdmin)
# admin_site.register(Sale, SaleAdmin)
# admin_site.register(Payment, PaymentAdmin)