from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Product
from .forms import ProductForm

@login_required
def product_list(request):
    """Display all products with search and filters"""
    products = Product.objects.all().order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(barcode__icontains=search_query)
        )
    
    # Filter by stock status
    stock_filter = request.GET.get('stock', '')
    if stock_filter == 'low':
        products = products.filter(stock__lte=10, stock__gt=0)
    elif stock_filter == 'out':
        products = products.filter(stock=0)
    elif stock_filter == 'available':
        products = products.filter(stock__gt=10)
    
    # Statistics
    total_products = Product.objects.count()
    low_stock = Product.objects.filter(stock__lte=10, stock__gt=0).count()
    out_of_stock = Product.objects.filter(stock=0).count()
    total_value = sum(p.price * p.stock for p in Product.objects.all())
    
    context = {
        'products': products,
        'search_query': search_query,
        'stock_filter': stock_filter,
        'total_products': total_products,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total_value': total_value,
    }
    return render(request, 'products/product_list.html', context)

@login_required
def product_add(request):
    """Add a new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('products:product_list')
    else:
        form = ProductForm()
    
    return render(request, 'products/product_form.html', {'form': form, 'action': 'Add'})

@login_required
def product_edit(request, pk):
    """Edit an existing product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('products:product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'products/product_form.html', {
        'form': form, 
        'action': 'Edit',
        'product': product
    })

@login_required
def product_delete(request, pk):
    """Delete a product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('products:product_list')
    
    return render(request, 'products/product_confirm_delete.html', {'product': product})

@login_required
def product_restock(request, pk):
    """Add stock to a product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        if quantity > 0:
            product.stock += quantity
            product.save()
            messages.success(request, f'Added {quantity} units to "{product.name}". New stock: {product.stock}')
        else:
            messages.error(request, 'Please enter a valid quantity.')
        return redirect('products:product_list')
    
    return render(request, 'products/product_restock.html', {'product': product})