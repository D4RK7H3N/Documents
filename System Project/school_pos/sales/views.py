from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from .models import Sale, SaleItem

@login_required
def sale_list(request):
    """Display all sales with search and filters"""
    sales = Sale.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        sales = sales.filter(
            Q(customer_name__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Date filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)
    
    # Statistics
    total_sales = Sale.objects.count()
    total_revenue = Sale.objects.aggregate(Sum('total'))['total__sum'] or 0
    
    context = {
        'sales': sales,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
    }
    return render(request, 'sales/sale_list.html', context)