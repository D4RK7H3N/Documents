from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal
from students.models import Student
from products.models import Product
from sales.models import Sale, SaleItem
from payments.models import Payment
from cashier.models import TuitionPayment


def dashboard(request):
    """Main cashier dashboard"""
    query = request.GET.get("q", "")
    student_query = request.GET.get("student_q", "")

    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all()

    if student_query:
        students = Student.objects.filter(
            Q(first_name__icontains=student_query) |
            Q(last_name__icontains=student_query) |
            Q(lrn__icontains=student_query)
        )
    else:
        students = Student.objects.all()

    return render(request, "cashier/dashboard.html", {
        "products": products,
        "students": students,
        "query": query,
        "student_query": student_query,
    })


@require_http_methods(["POST"])
def checkout(request):
    """Process checkout - handles both products and custom items"""
    try:
        # Get form data
        student_id = request.POST.get("student")
        customer_type = request.POST.get("customer_type", "walkin")
        customer_name = request.POST.get("customer_name", "").strip()
        product_ids = request.POST.getlist("products")
        quantities = request.POST.getlist("quantities")
        payment_method = request.POST.get("payment_method", "Cash")
        reference_number = request.POST.get('reference_number', '').strip()
        gcash_number = request.POST.get('gcash_number', '').strip()

        sale_student = None

        # Determine customer
        if customer_type == "student" and student_id:
            try:
                sale_student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                messages.error(request, "Selected student not found.")
                return redirect("cashier:dashboard")
        else:
            if not customer_name:
                customer_name = "Walk-in Customer"

        total_amount = Decimal('0')
        sale_items_data = []
        errors = []

        # Process regular products
        for product_id, qty in zip(product_ids, quantities):
            try:
                qty = int(qty)
            except (ValueError, TypeError):
                continue
                
            if qty <= 0:
                continue

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                errors.append(f"Product ID {product_id} not found")
                continue

            # Check stock
            if product.stock is not None and product.stock < qty:
                errors.append(f"Insufficient stock for {product.name}. Available: {product.stock}")
                continue

            subtotal = product.price * qty
            total_amount += subtotal

            sale_items_data.append({
                "product": product,
                "quantity": qty,
                "price": product.price,
                "is_custom": False,
            })

        # Process custom items
        custom_item_names = request.POST.getlist("custom_item_name")
        custom_item_prices = request.POST.getlist("custom_item_price")
        custom_item_quantities = request.POST.getlist("custom_item_qty")

        for name, price, qty in zip(custom_item_names, custom_item_prices, custom_item_quantities):
            if not name or not price:
                continue
                
            try:
                price = Decimal(str(price))
                qty = int(qty) if qty else 1
            except (ValueError, TypeError, Exception):
                errors.append(f"Invalid price or quantity for {name}")
                continue

            if qty <= 0 or price < 0:
                continue

            subtotal = price * qty
            total_amount += subtotal

            sale_items_data.append({
                "product": None,
                "name": name,
                "quantity": qty,
                "price": price,
                "is_custom": True,
            })

        # Handle errors
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("cashier:dashboard")

        if not sale_items_data:
            messages.error(request, "No valid products or custom items selected.")
            return redirect("cashier:dashboard")

        # Validate payment method
        if payment_method == 'GCash':
            if not reference_number:
                messages.error(request, "Reference number required for GCash")
                return redirect("cashier:dashboard")
            if not gcash_number:
                messages.error(request, "GCash number required")
                return redirect("cashier:dashboard")

        # Create Sale
        sale = Sale.objects.create(
            student=sale_student,
            customer_name=customer_name if customer_type == "walkin" else None,
            total=total_amount,
        )

        # Create SaleItems
        for item in sale_items_data:
            if item["is_custom"]:
                sale_item = SaleItem(
                    sale=sale,
                    product=None,
                    quantity=item["quantity"],
                    price=item["price"],
                )
                sale_item.custom_item_name = item["name"]
                sale_item.save()
            else:
                sale_item = SaleItem(
                    sale=sale,
                    product=item["product"],
                    quantity=item["quantity"],
                    price=item["price"],
                )
                sale_item.save()
                
                # Update stock
                if item["product"].stock is not None:
                    item["product"].stock -= item["quantity"]
                    item["product"].save()

        # Create Payment
        Payment.objects.create(
            sale=sale,
            amount=total_amount,
            payment_method=payment_method,
            reference_number=reference_number if payment_method == 'GCash' else '',
            gcash_number=gcash_number if payment_method == 'GCash' else '',
        )

        messages.success(request, f"Sale #{sale.id} completed successfully!")
        # Redirect to dashboard with sale_id parameter for modal popup
        return redirect(f"/cashier/?sale_id={sale.id}")

    except Exception as e:
        messages.error(request, f"Error processing sale: {str(e)}")
        return redirect("cashier:dashboard")


def receipt(request, sale_id):
    """Display receipt - returns HTML that can be used in modal or standalone"""
    try:
        sale = get_object_or_404(Sale, id=sale_id)
        items = sale.items.all()
        payment = sale.payments.first()

        # Determine customer
        if sale.student:
            customer = f"{sale.student.first_name} {sale.student.last_name}"
        elif sale.customer_name:
            customer = sale.customer_name
        else:
            customer = "Walk-in Customer"

        context = {
            "sale": sale,
            "items": items,      
            "payment": payment,   
            "customer": customer,
        }
        
        # Return JSON if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'sale': {
                    'id': sale.id,
                    'total': str(sale.total),
                    'created_at': sale.created_at.isoformat(),
                    'notes': getattr(sale, 'notes', '') or ''
                },
                'items': [{
                    'name': item.get_item_name(),
                    'quantity': item.quantity,
                    'price': str(item.price),
                    'subtotal': str(item.subtotal),
                    'product_id': item.product_id if item.product else None
                } for item in items],
                'payment': {
                    'payment_method': payment.payment_method if payment else 'Cash',
                    'gcash_number': payment.gcash_number if payment else '',
                    'reference_number': payment.reference_number if payment else ''
                } if payment else {'payment_method': 'Cash', 'gcash_number': '', 'reference_number': ''},
                'customer': customer,
                'cashier': request.user.get_full_name() or request.user.username
            })
        
        # Return HTML for regular requests
        return render(request, "cashier/receipt.html", context)
        
    except Exception as e:
        messages.error(request, f"Error loading receipt: {str(e)}")
        return redirect("cashier:dashboard")


def tuition_search(request):
    """Search students for tuition payment"""
    query = request.GET.get("q", "")
    students = []
    if query:
        students = Student.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(lrn__icontains=query)
        )
    return render(request, "students/tuition_search.html", {
        "students": students,
        "query": query,
    })


def add_tuition_payment(request, student_id):
    """Add tuition payment for a student"""
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        amount = request.POST.get("amount")
        method = request.POST.get("method")
        reference_no = request.POST.get("reference_no")
        remarks = request.POST.get("remarks")

        payment = TuitionPayment.objects.create(
            student=student,
            amount=amount,
            method=method,
            reference_no=reference_no,
            remarks=remarks,
            date=timezone.now(),
        )
        return redirect("cashier:tuition_receipt", payment_id=payment.id)

    return render(request, "students/add_payment.html", {"student": student})


def tuition_receipt(request, payment_id):
    """Display tuition payment receipt"""
    payment = get_object_or_404(TuitionPayment, id=payment_id)
    student = payment.student
 
    tuition_fee = student.tuition_fee if hasattr(student, "tuition_fee") else 0  
    total_paid = TuitionPayment.objects.filter(student=student).aggregate(Sum("amount"))["amount__sum"] or 0
    balance = tuition_fee - total_paid

    breakdown = None
    if student.display_level() in ["Senior High", "College"]:
        tuition_fee = 26000
        balance = tuition_fee - total_paid
        breakdown = {
            "first_sem": 5200,
            "first_quarter": 2600,
            "second_quarter": 2600,
            "second_sem": 5800,
            "third_quarter": 2900,
            "fourth_quarter": 2900,
        }

    context = {
        "student": student,
        "payment": payment,
        "tuition_fee": tuition_fee,
        "total_paid": total_paid,
        "balance": balance,
        "breakdown": breakdown,
    }
    return render(request, "students/tuition_receipt.html", context)