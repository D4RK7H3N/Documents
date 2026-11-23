from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from payments.models import Payment
from tuition.models import TuitionPayment
from sales.models import Sale
from assessment.models import AssessmentPayment
from dorm.models import DormPayment  # ADD THIS LINE
from datetime import datetime
from django.utils import timezone
from datetime import timedelta


@login_required
def revenue_dashboard(request):
    """Combined revenue dashboard for POS sales and tuition payments"""
    
    search_query = request.GET.get('search', '')
    revenue_type = request.GET.get('type', '') 
    payment_method = request.GET.get('method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    revenue_list = []
   
    # Get POS payments with sale items
    pos_payments = Payment.objects.all().select_related('sale', 'sale__student').prefetch_related('sale__items__product')
    
    # Get tuition payments
    tuition_payments = TuitionPayment.objects.all().select_related('student')
    
    # Get assessment payments
    assessment_payments = AssessmentPayment.objects.all().select_related('student', 'assessment_type')
    
    # Get dorm payments
    dorm_payments = DormPayment.objects.all().select_related('assignment', 'assignment__student', 'assignment__room')
    
    # Filter POS payments
    if revenue_type == '' or revenue_type == 'pos':
        if search_query:
            pos_payments = pos_payments.filter(
                Q(sale__customer_name__icontains=search_query) |
                Q(sale__student__first_name__icontains=search_query) |
                Q(sale__student__last_name__icontains=search_query) |
                Q(sale__student__lrn__icontains=search_query)
            )
        if payment_method:
            pos_payments = pos_payments.filter(payment_method=payment_method)
        if date_from:
            pos_payments = pos_payments.filter(created_at__date__gte=date_from)
        if date_to:
            pos_payments = pos_payments.filter(created_at__date__lte=date_to)
        
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

            # Get product details and determine type
            products_list = []
            has_product = False
            has_custom = False

            for item in payment.sale.items.all():
                # Use the model's get_item_name() method if available
                try:
                    product_name = item.get_item_name()
                except Exception:
                    product_name = "Unknown Item"

                if item.product:
                    has_product = True
                else:
                    has_custom = True

                products_list.append({
                    'name': product_name,
                    'quantity': item.quantity,
                    'price': item.price
                })

            # Determine type based on items
            if has_product and has_custom:
                item_type = 'Mixed'
            elif has_product:
                item_type = 'Product'
            elif has_custom:
                item_type = 'Custom'
            else:
                item_type = 'Sale'
            
            revenue_list.append({
                'id': payment.id,
                'type': item_type,
                'date': payment.created_at,
                'customer': customer,
                'amount': payment.amount,
                'method': payment.payment_method,
                'reference': payment.reference_number or '-',
                'receipt_url': 'cashier:receipt',
                'receipt_id': payment.sale.id,
                'products': products_list,
            })
    
    # Filter tuition payments
    if revenue_type == '' or revenue_type == 'tuition':
        if search_query:
            tuition_payments = tuition_payments.filter(
                Q(student__first_name__icontains=search_query) |
                Q(student__last_name__icontains=search_query) |
                Q(student__lrn__icontains=search_query)
            )
        if payment_method:
            tuition_payments = tuition_payments.filter(method=payment_method)
        if date_from:
            tuition_payments = tuition_payments.filter(date__date__gte=date_from)
        if date_to:
            tuition_payments = tuition_payments.filter(date__date__lte=date_to)
        
        for payment in tuition_payments:
            customer = f"{payment.student.first_name} {payment.student.last_name}"
            
            revenue_list.append({
                'id': payment.id,
                'type': 'Tuition',
                'date': payment.date,
                'customer': customer,
                'amount': payment.amount,
                'method': payment.method,
                'reference': payment.reference_no or '-',
                'receipt_url': 'students:tuition_receipt',
                'receipt_id': payment.id,
                'products': [{'name': 'Tuition Fee', 'quantity': 1, 'price': payment.amount}],
            })
    
    # Filter assessment payments
    if revenue_type == '' or revenue_type == 'assessment':
        if search_query:
            assessment_payments = assessment_payments.filter(
                Q(student__first_name__icontains=search_query) |
                Q(student__last_name__icontains=search_query) |
                Q(student__lrn__icontains=search_query)
            )
        if payment_method:
            assessment_payments = assessment_payments.filter(payment_method=payment_method)
        if date_from:
            assessment_payments = assessment_payments.filter(payment_date__date__gte=date_from)
        if date_to:
            assessment_payments = assessment_payments.filter(payment_date__date__lte=date_to)
        
        for payment in assessment_payments:
            customer = f"{payment.student.first_name} {payment.student.last_name}"
            assessment_name = payment.assessment_type.name if payment.assessment_type else 'Assessment'
            
            revenue_list.append({
                'id': payment.id,
                'type': 'Assessment',
                'date': payment.payment_date,
                'customer': customer,
                'amount': payment.amount,
                'method': payment.payment_method,
                'reference': payment.reference_number or '-',
                'receipt_url': 'cashier:assessment_receipt',
                'receipt_id': payment.id,
                'products': [{'name': assessment_name, 'quantity': 1, 'price': payment.amount}],
            })
    
    # Filter dorm payments
    if revenue_type == '' or revenue_type == 'dorm':
        if search_query:
            dorm_payments = dorm_payments.filter(
                Q(assignment__student__first_name__icontains=search_query) |
                Q(assignment__student__last_name__icontains=search_query) |
                Q(assignment__student__student_id__icontains=search_query)
            )
        if payment_method:
            dorm_payments = dorm_payments.filter(payment_method=payment_method)
        if date_from:
            dorm_payments = dorm_payments.filter(payment_date__date__gte=date_from)
        if date_to:
            dorm_payments = dorm_payments.filter(payment_date__date__lte=date_to)
        
        for payment in dorm_payments:
            customer = f"{payment.assignment.student.first_name} {payment.assignment.student.last_name}"
            dorm_info = payment.assignment.room.room_number if payment.assignment.room else 'Dorm'
            
            revenue_list.append({
                'id': payment.id,
                'type': 'Dorm',
                'date': payment.payment_date,
                'customer': customer,
                'amount': payment.amount,
                'method': payment.payment_method,
                'reference': payment.receipt_number or '-',
                'receipt_url': 'dorm:payment_receipt',
                'receipt_id': payment.id,
                'products': [{'name': f'Dorm - {dorm_info} ({payment.month_covered} {payment.year_covered})', 'quantity': 1, 'price': payment.amount}],
            })
    
    # Sort by date (newest first)
    revenue_list = sorted(revenue_list, key=lambda x: x['date'], reverse=True)
    
    # Calculate totals
    total_pos = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_tuition = TuitionPayment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_assessment = AssessmentPayment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_dorm = DormPayment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_revenue = total_pos + total_tuition + total_assessment + total_dorm
    
    # Count transactions
    pos_count = Payment.objects.count()
    tuition_count = TuitionPayment.objects.count()
    assessment_count = AssessmentPayment.objects.count()
    dorm_count = DormPayment.objects.count()
    total_transactions = pos_count + tuition_count + assessment_count + dorm_count
    
    context = {
        'revenue': revenue_list,
        'search_query': search_query,
        'revenue_type': revenue_type,
        'payment_method': payment_method,
        'date_from': date_from,
        'date_to': date_to,
        'total_revenue': total_revenue,
        'total_pos': total_pos,
        'total_tuition': total_tuition,
        'total_assessment': total_assessment,
        'total_dorm': total_dorm,
        'total_transactions': total_transactions,
        'pos_count': pos_count,
        'tuition_count': tuition_count,
        'assessment_count': assessment_count,
        'dorm_count': dorm_count,
    }
    return render(request, 'revenue/dashboard.html', context)


@login_required
def revenue_report(request):
    """Generate printable revenue/sales report"""
    
    # Get filter parameters
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    report_type = request.GET.get('type', 'all')
    
    # Parse dates and set defaults
    if date_from:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
    else:
        today = timezone.now().date()
        start_date = today.replace(day=1)
        date_from = start_date.strftime('%Y-%m-%d')
    
    if date_to:
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        end_date = end_date + timedelta(days=1)
    else:
        end_date = timezone.now().date() + timedelta(days=1)
        date_to = (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Initialize data
    pos_sales_list = []
    tuition_payments_list = []
    assessment_payments_list = []
    dorm_payments_list = []
    pos_sales_total = 0
    tuition_payments_total = 0
    assessment_payments_total = 0
    dorm_payments_total = 0
    
    # Get POS Sales with product details
    if report_type in ['all', 'pos']:
        pos_sales_query = Sale.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lt=end_date
        ).select_related('student').prefetch_related('payments', 'items__product').order_by('-created_at')
        
        for sale in pos_sales_query:
            if sale.student:
                customer = f"{sale.student.first_name} {sale.student.last_name}"
            elif sale.customer_name:
                customer = sale.customer_name
            else:
                customer = "Walk-in Customer"
            
            payment_method = "N/A"
            if sale.payments.exists():
                payment_method = sale.payments.first().payment_method
            
            # Get product details
            products_list = []
            for item in sale.items.all():
                try:
                    product_name = item.get_item_name()
                except Exception:
                    product_name = "Unknown Item"

                products_list.append({
                    'name': product_name,
                    'quantity': item.quantity,
                    'price': item.price
                })
            
            pos_sales_list.append({
                'id': sale.id,
                'date': sale.created_at,
                'customer': customer,
                'amount': sale.total,
                'method': payment_method,
                'reference': '-',
                'products': products_list,
            })
        
        pos_sales_total = pos_sales_query.aggregate(
            total=Sum('total')
        )['total'] or 0
    
    # Get Tuition Payments
    if report_type in ['all', 'tuition']:
        tuition_payments_query = TuitionPayment.objects.filter(
            date__gte=start_date,
            date__lt=end_date
        ).select_related('student').order_by('-date')
        
        for payment in tuition_payments_query:
            tuition_payments_list.append({
                'id': payment.id,
                'date': payment.date,
                'customer': f"{payment.student.first_name} {payment.student.last_name}",
                'amount': payment.amount,
                'method': payment.method,
                'reference': payment.reference_no or '-',
            })
        
        tuition_payments_total = tuition_payments_query.aggregate(
            total=Sum('amount')
        )['total'] or 0
    
    # Get Assessment Payments
    if report_type in ['all', 'assessment']:
        assessment_payments_query = AssessmentPayment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lt=end_date
        ).select_related('student', 'assessment_type').order_by('-payment_date')
        
        for payment in assessment_payments_query:
            assessment_payments_list.append({
                'id': payment.id,
                'date': payment.payment_date,
                'customer': f"{payment.student.first_name} {payment.student.last_name}",
                'amount': payment.amount,
                'method': payment.payment_method,
                'reference': payment.reference_number or '-',
                'assessment_type': payment.assessment_type.name,
            })
        
        assessment_payments_total = assessment_payments_query.aggregate(
            total=Sum('amount')
        )['total'] or 0
    
    # Get Dorm Payments - ADD THIS SECTION
    if report_type in ['all', 'dorm']:
        dorm_payments_query = DormPayment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lt=end_date
        ).select_related('assignment', 'assignment__student', 'assignment__room').order_by('-payment_date')
        
        for payment in dorm_payments_query:
            dorm_info = payment.assignment.room.room_number if payment.assignment.room else 'Dorm'
            dorm_payments_list.append({
                'id': payment.id,
                'date': payment.payment_date,
                'customer': f"{payment.assignment.student.first_name} {payment.assignment.student.last_name}",
                'amount': payment.amount,
                'method': payment.payment_method,
                'reference': payment.receipt_number or '-',
                'dorm_info': f"{dorm_info} ({payment.month_covered} {payment.year_covered})",
            })
        
        dorm_payments_total = dorm_payments_query.aggregate(
            total=Sum('amount')
        )['total'] or 0
    
    # Calculate grand total
    grand_total = pos_sales_total + tuition_payments_total + assessment_payments_total + dorm_payments_total
    
    # Count transactions
    pos_count = len(pos_sales_list)
    tuition_count = len(tuition_payments_list)
    assessment_count = len(assessment_payments_list)
    dorm_count = len(dorm_payments_list)
    total_transactions = pos_count + tuition_count + assessment_count + dorm_count
    
    context = {
        'pos_sales_list': pos_sales_list,
        'tuition_payments_list': tuition_payments_list,
        'assessment_payments_list': assessment_payments_list,
        'dorm_payments_list': dorm_payments_list,
        'pos_sales': pos_sales_total,
        'tuition_payments': tuition_payments_total,
        'assessment_payments': assessment_payments_total,
        'dorm_payments': dorm_payments_total,
        'total_revenue': grand_total,
        'pos_count': pos_count,
        'tuition_count': tuition_count,
        'assessment_count': assessment_count,
        'dorm_count': dorm_count,
        'total_transactions': total_transactions,
        'date_from': date_from,
        'date_to': date_to,
        'report_type': report_type,
        'generated_date': timezone.now(),
        'start_date': date_from,
        'end_date': date_to,
        'show_breakdown': True,
    }
    
    return render(request, 'revenue/report.html', context)