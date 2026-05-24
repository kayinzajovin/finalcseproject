# nyondoapp/views.py

# Django shortcuts: render templates, redirect URLs, fetch objects or return 404
from django.shortcuts import render, redirect, get_object_or_404

# Django auth: verify credentials, start/end user sessions
from django.contrib.auth import authenticate, login, logout

# Decorator to block unauthenticated users from protected views
from django.contrib.auth.decorators import login_required

# Flash messaging system for success/error feedback to the user
from django.contrib import messages

# Timezone-aware date and time utilities
from django.utils import timezone

# wraps: preserves original function name/docstring when writing decorators
from functools import wraps

# Decimal: precise currency arithmetic; InvalidOperation: catches bad decimal conversions
from decimal import Decimal, InvalidOperation

# defaultdict: auto-initialises missing keys used to group deposits by customer
from collections import defaultdict

# re: regular expressions for phone and NIN format validation
import re

# ORM models each maps to a database table
from .models import Product, Supplier, Sale, CustomerDeposit, StockArrival, Customer

# HttpResponse: return raw HTTP responses without a template
from django.http import HttpResponse

# render_to_string: render a template to a string (used for receipts/exports)
from django.template.loader import render_to_string


# Validation helpers ─

def is_valid_ugandan_phone(phone):
    # accepts 07XXXXXXXX, 256XXXXXXXXX, +256XXXXXXXXX
    return bool(re.match(r'^(\+256|256|0)7\d{8}$', phone.strip()))

def is_valid_nin(nin):
    # Uganda NIN: 14 alphanumeric characters (uppercase letters and digits)
    return bool(re.match(r'^[A-Z0-9]{14}$', nin.strip().upper()))

def parse_positive_decimal(value, field_name, min_value=1):
    # parse decimal from form input; returns (value, error) tuple
    try:
        result = Decimal(str(value).strip())
        if result < min_value:
            return None, f'{field_name} must be at least {min_value}.'
        return result, None
    except (InvalidOperation, ValueError):
        return None, f'{field_name} must be a valid number.'

def parse_positive_int(value, field_name, min_value=1):
    # parse integer from form input; returns (value, error) tuple
    try:
        result = int(str(value).strip())
        if result < min_value:
            return None, f'{field_name} must be at least {min_value}.'
        return result, None
    except (ValueError, TypeError):
        return None, f'{field_name} must be a whole number.'


# Role helpers

def get_user_role(user):
    # returns the first matching group name as the user's role
    groups = user.groups.values_list('name', flat=True)
    if 'admin' in groups:
        return 'admin'
    elif 'salesperson' in groups:
        return 'salesperson'
    elif 'stockmanager' in groups:
        return 'stockmanager'
    return None

def allowed_roles(roles, message=None):
    # decorator: blocks access if user's role is not in the allowed list
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)
            allowed = set(roles) if isinstance(roles, (list, tuple, set)) else {roles}
            if role not in allowed:
                if message:
                    messages.error(request, message)
                # redirect to the user's own dashboard
                if role == 'stockmanager':
                    return redirect('/dashboard/stockmanager/')
                if role == 'salesperson':
                    return redirect('/dashboard/salesperson/')
                return redirect('/dashboard/admin/')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# Public

def index(request):
    # homepage no login required
    return render(request, 'index.html')

def login_view(request):
    # authenticate user and redirect to their role dashboard
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # send to the correct dashboard based on group
            if user.groups.filter(name='admin').exists():
                return redirect('/dashboard/admin/')
            elif user.groups.filter(name='salesperson').exists():
                return redirect('/dashboard/salesperson/')
            elif user.groups.filter(name='stockmanager').exists():
                return redirect('/dashboard/stockmanager/')
            else:
                # logged in but no group assigned
                messages.error(request, 'No role assigned to this account.')
                logout(request)
                return render(request, 'login.html')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')

def logout_view(request):
    # clear session and send back to login
    logout(request)
    return redirect('/login/')


# Dashboards

@login_required
def dashboard_admin(request):
    # redirect non-admins to their own dashboard
    role = get_user_role(request.user)
    if role == 'salesperson':
        return redirect('/dashboard/salesperson/')
    if role == 'stockmanager':
        return redirect('/dashboard/stockmanager/')

    today      = timezone.now().date()
    this_month = timezone.now().month
    this_year  = timezone.now().year

    # stock summary
    total_stock = sum(p.quantity for p in Product.objects.all())
    low_stock   = Product.objects.filter(quantity__lt=10)

    # today's sales
    sales_today       = Sale.objects.filter(date__date=today)
    sales_today_total = sum(s.total_price for s in sales_today)
    sales_today_count = sales_today.count()

    # this month's revenue and profit
    sales_month    = Sale.objects.filter(date__month=this_month, date__year=this_year)
    revenue_month  = sum(s.total_price for s in sales_month)
    cost_month     = sum(s.unit_price * s.quantity for s in sales_month)
    gross_profit   = revenue_month - cost_month

    # deposit scheme stats
    deposit_members  = Customer.objects.count()
    pending_pickups  = CustomerDeposit.objects.filter(status='ready_pickup').count()

    # supplier credit summary
    suppliers            = Supplier.objects.all()
    supplier_credit_total = sum(s.credit_amount for s in suppliers)
    supplier_count       = suppliers.count()

    # 5 most recent sales for the activity feed
    recent_sales = Sale.objects.order_by('-date')[:5]

    context = {
        'total_stock': total_stock,
        'sales_today_total': sales_today_total,
        'sales_today_count': sales_today_count,
        'revenue_month': revenue_month,
        'cost_month': cost_month,
        'gross_profit': gross_profit,
        'low_stock': low_stock,
        'low_stock_count': low_stock.count(),
        'deposit_members': deposit_members,
        'pending_pickups': pending_pickups,
        'supplier_credit_total': supplier_credit_total,
        'supplier_count': supplier_count,
        'recent_sales': recent_sales,
        'suppliers': suppliers,
    }
    return render(request, 'dashboard_admin.html', context)


@login_required
def dashboard_salesperson(request):
    # redirect non-salespersons away
    role = get_user_role(request.user)
    if role == 'admin':
        return redirect('/dashboard/admin/')
    if role == 'stockmanager':
        return redirect('/dashboard/stockmanager/')

    today = timezone.now().date()

    # today's sales figures
    sales_today       = Sale.objects.filter(date__date=today)
    sales_today_total = sum(s.total_price for s in sales_today)
    sales_today_count = sales_today.count()
    transport_today   = sum(s.transport_fee for s in sales_today)

    # today's deposit activity
    deposits_today       = CustomerDeposit.objects.filter(date=today)
    deposits_today_total = sum(d.amount_deposited for d in deposits_today)
    deposits_today_count = deposits_today.count()

    # quick counts for the dashboard cards
    total_stock      = Product.objects.filter(quantity__gt=0).count()
    new_customers    = Customer.objects.filter(registration_date=today).count()
    pending_pickups  = CustomerDeposit.objects.filter(status='ready_pickup')
    pending_count    = pending_pickups.count()
    recent_sales     = Sale.objects.order_by('-date')[:5]

    context = {
        'sales_today_total': sales_today_total,
        'sales_today_count': sales_today_count,
        'deposits_today_total': deposits_today_total,
        'deposits_today_count': deposits_today_count,
        'total_stock': total_stock,
        'new_customers': new_customers,
        'pending_pickups': pending_pickups,
        'pending_count': pending_count,
        'transport_today': transport_today,
        'recent_sales': recent_sales,
    }
    return render(request, 'dashboard_salesperson.html', context)


@login_required
def dashboard_stockmanager(request):
    # redirect non-stockmanagers away
    role = get_user_role(request.user)
    if role == 'admin':
        return redirect('/dashboard/admin/')
    if role == 'salesperson':
        return redirect('/dashboard/salesperson/')

    products = Product.objects.all()
    suppliers = Supplier.objects.all()

    # stock level breakdown for dashboard cards
    total_stock    = sum(p.quantity for p in products)
    critical_stock = Product.objects.filter(quantity__lt=5)
    critical_count = critical_stock.count()
    low_stock_count = Product.objects.filter(quantity__gte=5, quantity__lt=10).count()
    well_stocked   = Product.objects.filter(quantity__gte=10).count()

    # financial value of current stock
    stock_cost_value = sum(p.unit_cost * p.quantity for p in products)
    stock_sell_value = sum(p.unit_price * p.quantity for p in products)

    # supplier credit overview
    supplier_credit_total = sum(s.credit_amount for s in suppliers)
    supplier_count        = suppliers.count()

    # recent arrivals feed
    recent_arrivals     = StockArrival.objects.order_by('-date')[:5]
    week_ago            = timezone.now() - timezone.timedelta(days=7)
    arrivals_this_week  = StockArrival.objects.filter(date__gte=week_ago).count()

    context = {
        'total_stock': total_stock,
        'critical_count': critical_count,
        'low_stock_count': low_stock_count,
        'well_stocked': well_stocked,
        'products': products,
        'suppliers': suppliers,
        'supplier_credit_total': supplier_credit_total,
        'supplier_count': supplier_count,
        'stock_cost_value': stock_cost_value,
        'stock_sell_value': stock_sell_value,
        'recent_arrivals': recent_arrivals,
        'arrivals_this_week': arrivals_this_week,
        'critical_stock': critical_stock,
    }
    return render(request, 'dashboard_stockmanager.html', context)


# Stock─

@login_required
def stock(request):
    # salesperson has no access to stock management
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to access stock management.')
        return redirect('/dashboard/salesperson/')

    if request.method == 'POST':
        product_name   = request.POST.get('product_name', '').strip()
        supplier_name  = request.POST.get('supplier_name', '').strip()
        quantity_raw   = request.POST.get('quantity', '')
        unit_cost_raw  = request.POST.get('unit_cost', '')
        unit_price_raw = request.POST.get('unit_price', '')
        products       = Product.objects.all()

        # all fields are required
        if not product_name or not supplier_name or not quantity_raw or not unit_cost_raw or not unit_price_raw:
            messages.error(request, 'Please fill in all required fields before saving.')
            return render(request, 'stock.html', {'products': products})

        # validate each numeric field
        quantity, err = parse_positive_int(quantity_raw, 'Quantity')
        if err:
            messages.error(request, err)
            return render(request, 'stock.html', {'products': products})

        unit_cost, err = parse_positive_decimal(unit_cost_raw, 'Unit cost')
        if err:
            messages.error(request, err)
            return render(request, 'stock.html', {'products': products})

        unit_price, err = parse_positive_decimal(unit_price_raw, 'Unit price')
        if err:
            messages.error(request, err)
            return render(request, 'stock.html', {'products': products})

        # selling price must never be below buying price
        if unit_price < unit_cost:
            messages.error(request, 'Selling price cannot be less than buying price.')
            return render(request, 'stock.html', {'products': products})

        # create or update the product and add to its stock quantity
        product, created = Product.objects.get_or_create(
            name=product_name,
            defaults={'unit_cost': unit_cost, 'unit_price': unit_price, 'quantity': 0}
        )
        product.unit_cost   = unit_cost
        product.unit_price  = unit_price
        product.quantity   += quantity
        product.save()

        # create supplier if they don't exist yet
        supplier, _ = Supplier.objects.get_or_create(
            name=supplier_name,
            defaults={'phone': ''}
        )

        # record this delivery as a stock arrival
        StockArrival.objects.create(
            product=product,
            supplier=supplier,
            quantity_received=quantity,
            unit_cost=unit_cost,
            unit_price=unit_price,
        )

        messages.success(request, f'{product_name} stock saved successfully!')
        return redirect('stock')

    products = Product.objects.all()
    return render(request, 'stock.html', {'products': products})


@login_required
def stock_edit(request, pk):
    # salesperson cannot edit stock
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to edit stock.')
        return redirect('/dashboard/salesperson/')

    product = get_object_or_404(Product, id=pk)

    if request.method == 'POST':
        name           = request.POST.get('name', '').strip()
        unit_cost_raw  = request.POST.get('unit_cost', '')
        unit_price_raw = request.POST.get('unit_price', '')
        quantity_raw   = request.POST.get('quantity', '')

        if not name:
            messages.error(request, 'Product name is required.')
            return render(request, 'stock_edit.html', {'product': product})

        # quantity can be 0 (out of stock) but not negative
        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err:
            messages.error(request, err)
            return render(request, 'stock_edit.html', {'product': product})

        unit_cost, err = parse_positive_decimal(unit_cost_raw, 'Unit cost')
        if err:
            messages.error(request, err)
            return render(request, 'stock_edit.html', {'product': product})

        unit_price, err = parse_positive_decimal(unit_price_raw, 'Unit price')
        if err:
            messages.error(request, err)
            return render(request, 'stock_edit.html', {'product': product})

        # selling price must not be below buying price
        if unit_price < unit_cost:
            messages.error(request, 'Selling price cannot be less than buying price.')
            return render(request, 'stock_edit.html', {'product': product})

        product.name       = name
        product.unit_cost  = unit_cost
        product.unit_price = unit_price
        product.quantity   = quantity
        product.save()
        messages.success(request, f'{product.name} updated successfully!')
        return redirect('stock')

    return render(request, 'stock_edit.html', {'product': product})


@login_required
def stock_delete(request, pk):
    # salesperson cannot delete stock
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to delete stock.')
        return redirect('/dashboard/salesperson/')

    product = get_object_or_404(Product, id=pk)
    name = product.name
    product.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('stock')


# Sales─

@login_required
def sales(request):
    # stockmanager can view sales but cannot record them
    role     = get_user_role(request.user)
    sales_qs = Sale.objects.all().order_by('-date')
    products = Product.objects.all()

    if request.method == 'POST' and role == 'stockmanager':
        messages.error(request, 'You are not authorized to record sales.')
        return redirect('/dashboard/stockmanager/')

    if request.method == 'POST':
        product_id   = request.POST.get('product_id')
        quantity_raw = request.POST.get('quantity', '')
        distance_raw = request.POST.get('distance_km', '0') or '0'

        if not product_id:
            messages.error(request, 'Please select a product.')
            return render(request, 'sales.html', {'sales': sales_qs, 'products': products})

        # quantity must be at least 1
        quantity, err = parse_positive_int(quantity_raw, 'Quantity')
        if err:
            messages.error(request, err)
            return render(request, 'sales.html', {'sales': sales_qs, 'products': products})

        # distance can be 0 (customer pickup)
        distance, err = parse_positive_decimal(distance_raw, 'Distance', min_value=0)
        if err:
            messages.error(request, err)
            return render(request, 'sales.html', {'sales': sales_qs, 'products': products})

        product = get_object_or_404(Product, id=product_id)

        # block sale if requested quantity exceeds available stock
        if quantity > product.quantity:
            messages.error(request, f'Not enough stock. Only {product.quantity} units available.')
            return render(request, 'sales.html', {'sales': sales_qs, 'products': products})

        total_price = product.unit_price * quantity

        # Sale.save() auto-calculates transport_fee
        Sale.objects.create(
            product=product,
            quantity=quantity,
            unit_price=product.unit_price,
            total_price=total_price,
            distance_km=distance,
        )

        # deduct sold quantity from product stock
        product.quantity -= quantity
        product.save()

        messages.success(request, f'Sale recorded for {product.name}!')
        return redirect('sales')

    return render(request, 'sales.html', {'sales': sales_qs, 'products': products})


@login_required
def sales_edit(request, pk):
    # stockmanager cannot edit sales
    role     = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit sales.')
        return redirect('/dashboard/stockmanager/')

    sale     = get_object_or_404(Sale, id=pk)
    products = Product.objects.all()

    if request.method == 'POST':
        product_id   = request.POST.get('product_id')
        quantity_raw = request.POST.get('quantity', '')
        distance_raw = request.POST.get('distance_km', '0') or '0'

        quantity, err = parse_positive_int(quantity_raw, 'Quantity')
        if err:
            messages.error(request, err)
            return render(request, 'sales_edit.html', {'sale': sale, 'products': products})

        distance, err = parse_positive_decimal(distance_raw, 'Distance', min_value=0)
        if err:
            messages.error(request, err)
            return render(request, 'sales_edit.html', {'sale': sale, 'products': products})

        product = get_object_or_404(Product, id=product_id)

        # add back original quantity before checking if new quantity is available
        available_stock = product.quantity + sale.quantity
        if quantity > available_stock:
            messages.error(request, f'Not enough stock. Only {available_stock} units available.')
            return render(request, 'sales_edit.html', {'sale': sale, 'products': products})

        total_price   = product.unit_price * quantity
        transport_fee = 0 if total_price >= 500000 and distance <= 10 else 30000

        # if product changed, restore old product's stock separately
        if sale.product != product:
            sale.product.quantity += sale.quantity
            sale.product.save()
            product.quantity -= quantity
        else:
            # same product just adjust the difference
            product.quantity += sale.quantity - quantity

        product.save()

        sale.product       = product
        sale.quantity      = quantity
        sale.unit_price    = product.unit_price
        sale.total_price   = total_price
        sale.distance_km   = distance
        sale.transport_fee = transport_fee
        sale.save()

        messages.success(request, 'Sale updated successfully!')
        return redirect('sales')

    return render(request, 'sales_edit.html', {'sale': sale, 'products': products})


@login_required
def sales_delete(request, pk):
    # stockmanager cannot delete sales
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete sales.')
        return redirect('/dashboard/stockmanager/')

    sale    = get_object_or_404(Sale, id=pk)
    product = sale.product

    # restore stock when a sale is deleted
    product.quantity += sale.quantity
    product.save()
    sale.delete()
    messages.success(request, 'Sale deleted and stock restored!')
    return redirect('sales')


# Suppliers─

@login_required
def supplier_credit(request):
    # salesperson has no access to supplier credit
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to access supplier credit.')
        return redirect('/dashboard/salesperson/')

    if request.method == 'POST':
        name         = request.POST.get('name', '').strip()
        phone        = request.POST.get('phone', '').strip()
        address      = request.POST.get('address', '').strip()
        product_id   = request.POST.get('product_id')
        quantity_raw = request.POST.get('quantity', '0') or '0'
        credit_raw   = request.POST.get('credit_amount', '')
        products     = Product.objects.all()
        suppliers    = Supplier.objects.all()

        # helper to re-render form with an error message
        def render_form(error):
            messages.error(request, error)
            return render(request, 'supplier_credit.html', {
                'suppliers': suppliers, 'products': products,
            })

        if not name:
            return render_form('Supplier name is required.')
        if not credit_raw:
            return render_form('Credit amount is required.')

        # validate phone format if provided
        if phone and not is_valid_ugandan_phone(phone):
            return render_form('Enter a valid Ugandan phone number e.g. 0712345678.')

        # credit can be 0 (no debt yet) but not negative
        credit_amount, err = parse_positive_decimal(credit_raw, 'Credit amount', min_value=0)
        if err:
            return render_form(err)

        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err:
            return render_form(err)

        product = get_object_or_404(Product, id=product_id) if product_id else None

        # create supplier if new, otherwise update their record
        supplier, created = Supplier.objects.get_or_create(
            name=name,
            defaults={
                'phone': phone, 'address': address,
                'product': product, 'quantity': quantity,
                'credit_amount': credit_amount,
            }
        )
        if not created:
            supplier.credit_amount = credit_amount
            supplier.phone         = phone
            supplier.address       = address
            supplier.product       = product
            supplier.quantity      = quantity
            supplier.save()

        messages.success(request, f'Supplier {name} credit saved!')
        return redirect('supplier_credit')

    suppliers           = Supplier.objects.all()
    total_credit        = sum(s.credit_amount for s in suppliers)
    supplier_count      = suppliers.count()
    suppliers_with_debt = suppliers.filter(credit_amount__gt=0).count()
    products            = Product.objects.all()

    return render(request, 'supplier_credit.html', {
        'suppliers': suppliers,
        'total_credit': total_credit,
        'supplier_count': supplier_count,
        'suppliers_with_debt': suppliers_with_debt,
        'products': products,
    })


@login_required
def supplier_edit(request, pk):
    # salesperson cannot edit suppliers
    role     = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to edit suppliers.')
        return redirect('/dashboard/salesperson/')

    supplier = get_object_or_404(Supplier, id=pk)
    products = Product.objects.all()

    if request.method == 'POST':
        name         = request.POST.get('name', '').strip()
        phone        = request.POST.get('phone', '').strip()
        address      = request.POST.get('address', '').strip()
        quantity_raw = request.POST.get('quantity', '0') or '0'
        credit_raw   = request.POST.get('credit_amount', '')
        product_id   = request.POST.get('product_id')

        if not name:
            messages.error(request, 'Supplier name is required.')
            return render(request, 'supplier_edit.html', {'supplier': supplier, 'products': products})

        if phone and not is_valid_ugandan_phone(phone):
            messages.error(request, 'Enter a valid Ugandan phone number e.g. 0712345678.')
            return render(request, 'supplier_edit.html', {'supplier': supplier, 'products': products})

        credit_amount, err = parse_positive_decimal(credit_raw, 'Credit amount', min_value=0)
        if err:
            messages.error(request, err)
            return render(request, 'supplier_edit.html', {'supplier': supplier, 'products': products})

        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err:
            messages.error(request, err)
            return render(request, 'supplier_edit.html', {'supplier': supplier, 'products': products})

        supplier.name          = name
        supplier.phone         = phone
        supplier.address       = address
        supplier.quantity      = quantity
        supplier.credit_amount = credit_amount
        supplier.product       = get_object_or_404(Product, id=product_id) if product_id else None
        supplier.save()
        messages.success(request, f'{supplier.name} updated successfully!')
        return redirect('supplier_credit')

    return render(request, 'supplier_edit.html', {'supplier': supplier, 'products': products})


@login_required
def supplier_delete(request, pk):
    # salesperson cannot delete suppliers
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to delete suppliers.')
        return redirect('/dashboard/salesperson/')

    supplier = get_object_or_404(Supplier, id=pk)
    name = supplier.name
    supplier.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('supplier_credit')


# Customers─

@login_required
def customer_registration(request):
    # stockmanager cannot register customers
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to access customer registration.')
        return redirect('/dashboard/stockmanager/')

    if request.method == 'POST':
        full_name         = request.POST.get('full_name', '').strip()
        NIN               = request.POST.get('NIN', '').strip().upper()
        phone             = request.POST.get('phone', '').strip()
        employer          = request.POST.get('employer', '').strip()
        address           = request.POST.get('address', '').strip()
        preferred_product = request.POST.get('preferred_product', '').strip()
        customers         = Customer.objects.all()

        def render_form(error):
            messages.error(request, error)
            return render(request, 'customer_registration.html', {'customers': customers})

        # name, NIN, phone are mandatory
        if not full_name or not NIN or not phone:
            return render_form('Full name, NIN and phone number are required.')

        # NIN must match Uganda format
        if not is_valid_nin(NIN):
            return render_form('Invalid NIN. Expected format: CM20100012345678 (2 letters + 14 digits).')

        # phone must be a valid Ugandan number
        if not is_valid_ugandan_phone(phone):
            return render_form('Enter a valid Ugandan phone number e.g. 0712345678.')

        # NIN must be unique one registration per person
        if Customer.objects.filter(NIN=NIN).exists():
            return render_form(f'A customer with NIN {NIN} is already registered.')

        Customer.objects.create(
            full_name=full_name, NIN=NIN, phone=phone,
            employer=employer, address=address,
            preferred_product=preferred_product,
        )
        messages.success(request, f'{full_name} registered successfully!')
        return redirect('customer_registration')

    customers = Customer.objects.all()
    return render(request, 'customer_registration.html', {'customers': customers})


@login_required
def customer_edit(request, pk):
    # stockmanager cannot edit customers
    role     = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit customers.')
        return redirect('/dashboard/stockmanager/')

    customer = get_object_or_404(Customer, id=pk)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        NIN       = request.POST.get('NIN', '').strip().upper()
        phone     = request.POST.get('phone', '').strip()

        if not full_name or not NIN or not phone:
            messages.error(request, 'Full name, NIN and phone are required.')
            return render(request, 'customer_edit.html', {'customer': customer})

        if not is_valid_nin(NIN):
            messages.error(request, 'Invalid NIN format. Expected: CM20100012345678.')
            return render(request, 'customer_edit.html', {'customer': customer})

        if not is_valid_ugandan_phone(phone):
            messages.error(request, 'Enter a valid Ugandan phone number e.g. 0712345678.')
            return render(request, 'customer_edit.html', {'customer': customer})

        # exclude current customer so their own NIN doesn't trigger a duplicate error
        if Customer.objects.filter(NIN=NIN).exclude(id=pk).exists():
            messages.error(request, f'Another customer already has NIN {NIN}.')
            return render(request, 'customer_edit.html', {'customer': customer})

        customer.full_name         = full_name
        customer.NIN               = NIN
        customer.phone             = phone
        customer.employer          = request.POST.get('employer', '').strip()
        customer.address           = request.POST.get('address', '').strip()
        customer.preferred_product = request.POST.get('preferred_product', '').strip()
        customer.save()
        messages.success(request, f'{customer.full_name} updated successfully!')
        return redirect('customer_registration')

    return render(request, 'customer_edit.html', {'customer': customer})


@login_required
def customer_delete(request, pk):
    # stockmanager cannot delete customers
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete customers.')
        return redirect('/dashboard/stockmanager/')

    customer = get_object_or_404(Customer, id=pk)
    name = customer.full_name
    customer.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('customer_registration')


# Customer Deposits 

@login_required
def customer_deposit(request):
    # stockmanager cannot access deposits
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to access customer deposits.')
        return redirect('/dashboard/stockmanager/')

    def build_groups():
        # group all deposits by customer with running totals
        all_deposits = CustomerDeposit.objects.select_related(
            'customer', 'product'
        ).order_by('customer__full_name', '-date')

        grouped = defaultdict(list)
        for d in all_deposits:
            grouped[d.customer].append(d)

        customer_groups = []
        for customer, dep_list in grouped.items():
            total_deposited   = sum(d.amount_deposited for d in dep_list)
            total_paid_pickup = sum(d.amount_paid_on_pickup for d in dep_list)
            remaining         = total_deposited - total_paid_pickup
            total_units       = sum(d.units_equivalent for d in dep_list)
            customer_groups.append({
                'customer':          customer,
                'deposits':          dep_list,
                'total_deposited':   total_deposited,
                'total_paid_pickup': total_paid_pickup,
                'remaining':         remaining,
                'total_units':       total_units,
            })
        return customer_groups

    if request.method == 'POST':
        nin            = request.POST.get('nin', '').strip()
        product_id     = request.POST.get('product_id')
        amount_raw     = request.POST.get('amount_deposited', '')
        payment_method = request.POST.get('payment_method', 'cash')
        payment_date   = request.POST.get('payment_date', '')

        def render_form(error):
            messages.error(request, error)
            return render(request, 'customer_deposit.html', {
                'customer_groups': build_groups(),
                'products': Product.objects.all(),
            })

        if not nin or not product_id or not amount_raw:
            return render_form('Please fill in all required fields.')

        # deposit must be at least 1 UGX
        amount_deposited, err = parse_positive_decimal(amount_raw, 'Deposit amount')
        if err:
            return render_form(err)

        # look up customer by NIN
        try:
            customer = Customer.objects.get(NIN=nin)
        except Customer.DoesNotExist:
            return render_form(f'No customer found with NIN {nin}.')

        product      = get_object_or_404(Product, id=product_id)
        quantity_raw = request.POST.get('quantity', '0') or '0'

        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err:
            return render_form(err)

        # CustomerDeposit.save() auto-calculates units_equivalent
        deposit = CustomerDeposit.objects.create(
            customer=customer,
            product=product,
            amount_deposited=amount_deposited,
            unit_price=product.unit_price,
            quantity=quantity,
            payment_method=payment_method,
        )

        # override date if a specific payment date was given
        if payment_date:
            deposit.date = payment_date
            deposit.save()

        messages.success(request, f'Deposit of UGX {int(amount_deposited):,} recorded for {customer.full_name}!')
        return redirect('customer_deposit')

    return render(request, 'customer_deposit.html', {
        'customer_groups': build_groups(),
        'products': Product.objects.all(),
    })


@login_required
def deposit_edit(request, pk):
    # stockmanager cannot edit deposits
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit deposits.')
        return redirect('/dashboard/stockmanager/')

    deposit = get_object_or_404(CustomerDeposit, id=pk)

    if request.method == 'POST':
        new_status   = request.POST.get('status', deposit.status)
        pickup_raw   = request.POST.get('amount_paid_on_pickup', '0') or '0'
        quantity_raw = request.POST.get('quantity', str(deposit.quantity)) or str(deposit.quantity)

        # status must be one of the defined choices
        status_order = ['active', 'ready_pickup', 'collected']
        if new_status not in status_order:
            messages.error(request, 'Invalid status selected.')
            return render(request, 'deposit_edit.html', {'deposit': deposit})

        # status can only move forward no reversals allowed
        if status_order.index(new_status) < status_order.index(deposit.status):
            messages.error(request, f'Cannot revert status from "{deposit.status}" back to "{new_status}".')
            return render(request, 'deposit_edit.html', {'deposit': deposit})

        # pickup amount can be 0 if not yet collected
        amount_paid, err = parse_positive_decimal(pickup_raw, 'Amount paid on pickup', min_value=0)
        if err:
            messages.error(request, err)
            return render(request, 'deposit_edit.html', {'deposit': deposit})

        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err:
            messages.error(request, err)
            return render(request, 'deposit_edit.html', {'deposit': deposit})

        # only update these three fields never touch the original deposit date
        deposit.status                = new_status
        deposit.amount_paid_on_pickup = amount_paid
        deposit.quantity              = quantity
        deposit.save(update_fields=['status', 'amount_paid_on_pickup', 'quantity'])

        messages.success(request, 'Deposit updated successfully!')
        return redirect('customer_deposit')

    return render(request, 'deposit_edit.html', {'deposit': deposit})


@login_required
def deposit_delete(request, pk):
    # stockmanager cannot delete deposits
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete deposits.')
        return redirect('/dashboard/stockmanager/')

    deposit = get_object_or_404(CustomerDeposit, id=pk)
    deposit.delete()
    messages.success(request, 'Deposit deleted successfully!')
    return redirect('customer_deposit')


# Supplier Payment ─

@login_required
@allowed_roles(['admin', 'stockmanager'], message='You are not authorized to access supplier payments.')
def supplier_pay(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        try:
            amount_paid = Decimal(request.POST.get('amount_paid', '0').strip())
        except InvalidOperation:
            messages.error(request, 'Invalid amount. Please enter a valid number.')
            return redirect(f'/supplier_credit/pay/{supplier_id}/')

        # amount must be positive
        if amount_paid <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect(f'/supplier_credit/pay/{supplier_id}/')

        # cannot pay more than what is owed
        if amount_paid > supplier.credit_amount:
            messages.error(request, f'Amount exceeds balance of UGX {supplier.credit_amount:,.0f}.')
            return redirect(f'/supplier_credit/pay/{supplier_id}/')

        # deduct payment from supplier's outstanding credit
        supplier.credit_amount -= amount_paid
        supplier.save()
        messages.success(request, f'UGX {amount_paid:,.0f} paid. Remaining: UGX {supplier.credit_amount:,.0f}.')
        return redirect('/supplier_credit/')

    # GET show the payment form
    return render(request, 'supplier_pay.html', {'supplier': supplier})


# Receipt─

@login_required
def sale_receipt(request, pk):
    # fetch sale and render a printable receipt template
    sale = get_object_or_404(Sale, id=pk)
    return render(request, 'sale_receipt.html', {'sale': sale})