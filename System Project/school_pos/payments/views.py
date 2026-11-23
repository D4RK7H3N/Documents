from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from .models import Payment
from cashier.models import TuitionPayment  # Fixed import


@login_required
def payment_list(request):
    """Display all payments (POS sales and tuition)"""
    
    # Get filters
    search_query = request.GET.get('search', '')
    payment_type = request.GET.get('type', '')  # 'pos' or 'tuition' or ''
    payment_method = request.GET.get('method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Get POS payments
    pos_payments = Payment.objects.all().select_related('sale', 'sale__student')
    
    # Get Tuition payments
    tuition_payments = TuitionPayment.objects.all().select_related('student')
    
    # Apply filters
    if search_query:
        pos_payments = pos_payments.filter(
            Q(sale__customer_name__icontains=search_query) |
            Q(sale__student__first_name__icontains=search_query) |
            Q(sale__student__last_name__icontains=search_query) |
            Q(sale__student__lrn__icontains=search_query)
        )
        tuition_payments = tuition_payments.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__lrn__icontains=search_query)
        )
    
    if payment_method:
        pos_payments = pos_payments.filter(payment_method=payment_method)
        tuition_payments = tuition_payments.filter(method=payment_method)
    
    if date_from:
        # Fixed: Use created_at instead of date
        pos_payments = pos_payments.filter(created_at__date__gte=date_from)
        tuition_payments = tuition_payments.filter(date__date__gte=date_from)
    
    if date_to:
        # Fixed: Use created_at instead of date
        pos_payments = pos_payments.filter(created_at__date__lte=date_to)
        tuition_payments = tuition_payments.filter(date__date__lte=date_to)
    
    # Combine and prepare data
    payments_list = []
    
    # Add POS payments
    if payment_type == '' or payment_type == 'pos':
        for payment in pos_payments:
            if not payment.sale:
                continue
            customer = ''
            if payment.sale.student:
                customer = f"{payment.sale.student.first_name} {payment.sale.student.last_name}"
            elif payment.sale.customer_name:
                customer = payment.sale.customer_name
            else:
                customer = "Walk-in Customer"

            payments_list.append({
                'id': payment.id,
                'type': 'POS Sale',
                'date': payment.created_at,  # Fixed: Use created_at
                'customer': customer,
                'amount': payment.amount,
                'method': payment.payment_method,
                'reference': payment.reference_number or '-',
                'receipt_url': 'cashier:receipt',
                'receipt_id': payment.sale.id,
            })
    
    # Add Tuition payments
    if payment_type == '' or payment_type == 'tuition':
        for payment in tuition_payments:
            customer = f"{payment.student.first_name} {payment.student.last_name}"
            
            payments_list.append({
                'id': payment.id,
                'type': 'Tuition',
                'date': payment.date,
                'customer': customer,
                'amount': payment.amount,
                'method': payment.method,
                'reference': payment.reference_no or '-',
                'receipt_url': 'cashier:tuition_receipt',
                'receipt_id': payment.id,
            })
    
    # Sort by date (newest first)
    payments_list = sorted(payments_list, key=lambda x: x['date'], reverse=True)
    
    # Calculate statistics
    total_pos = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_tuition = TuitionPayment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_amount = total_pos + total_tuition
    total_count = len(payments_list)
    
    context = {
        'payments': payments_list,
        'search_query': search_query,
        'payment_type': payment_type,
        'payment_method': payment_method,
        'date_from': date_from,
        'date_to': date_to,
        'total_count': total_count,
        'total_amount': total_amount,
        'total_pos': total_pos,
        'total_tuition': total_tuition,
    }
    return render(request, 'payments/payment_list.html', context)