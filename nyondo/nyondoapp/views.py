# nyondoapp/views.py
#
# Central view module for the Nyondo application.
# Handles all HTTP request/response logic for: authentication, role-based dashboards,
# stock management, sales, suppliers, customers, and customer deposits.

# Import the context module from Python's multiprocessing package
from multiprocessing import context

# Import Django shortcuts used to render pages, redirect users, and fetch objects safely
from django.shortcuts import render, redirect, get_object_or_404

# Import functions used for user authentication (login verification)
from django.contrib.auth import authenticate, login, logout

# Import decorator that restricts views to logged-in users only
from django.contrib.auth.decorators import login_required

# Import Django's messaging framework for displaying success, error, and warning messages
from django.contrib import messages

# Import Django timezone utilities for working with dates and times
from django.utils import timezone

# Import wraps decorator used when creating custom decorators
from functools import wraps

# Import Decimal for accurate money calculations and InvalidOperation for handling decimal errors
from decimal import Decimal, InvalidOperation

# Import defaultdict, a dictionary that automatically creates default values
from collections import defaultdict

# Import Python's regular expression module for pattern matching and validation
import re

# Import application models used to interact with database tables
from .models import (
    Product,          # Stores product information
    Supplier,         # Stores supplier information
    Sale,             # Stores sales records
    CustomerDeposit,  # Stores customer deposit records
    StockArrival,     # Stores stock arrival records
    Customer          # Stores customer information
)

# Import HttpResponse for returning custom HTTP responses
from django.http import HttpResponse

# Import render_to_string to convert HTML templates into text strings
from django.template.loader import render_to_string




# VALIDATION HELPERS
# Reusable input-validation utilities shared across all views.
# These centralise error messages and keep view logic free of boilerplate.


def is_valid_ugandan_phone(phone):
    """
    Return True if `phone` matches a valid Ugandan mobile number.
    Accepted formats: 07XXXXXXXX  |  256XXXXXXXXX  |  +256XXXXXXXXX
    """
    return bool(re.match(r'^(\+256|256|0)7\d{8}$', phone.strip()))


def is_valid_nin(nin):
    """
    Return True if `nin` matches the Uganda National Identification Number format:
    exactly 14 uppercase alphanumeric characters (e.g. CM20100012345678).
    """
    return bool(re.match(r'^[A-Z0-9]{14}$', nin.strip().upper()))


def parse_positive_decimal(value, field_name, min_value=1):
    """
    Safely parse `value` into a Decimal.

    Args:
        value:      Raw string from POST data.
        field_name: Human-readable label used in error messages.
        min_value:  Minimum acceptable value (default 1). Pass 0 to allow zero.

    Returns:
        (Decimal, None)  on success.
        (None, str)      on failure, where str is a user-facing error message.
    """
    try:
        result = Decimal(str(value).strip())
        if result < min_value:
            return None, f'{field_name} must be at least {min_value}.'
        return result, None
    except (InvalidOperation, ValueError):
        return None, f'{field_name} must be a valid number.'


def parse_positive_int(value, field_name, min_value=1):
    """
    Safely parse `value` into an integer.

    Args:
        value:      Raw string from POST data.
        field_name: Human-readable label used in error messages.
        min_value:  Minimum acceptable value (default 1). Pass 0 to allow zero.

    Returns:
        (int, None)  on success.
        (None, str)  on failure, where str is a user-facing error message.
    """
    try:
        result = int(str(value).strip())
        if result < min_value:
            return None, f'{field_name} must be at least {min_value}.'
        return result, None
    except (ValueError, TypeError):
        return None, f'{field_name} must be a whole number.'



# ROLE HELPERS
# The app uses three Django groups — admin, salesperson, stockmanager — to
# control access. These helpers resolve a user's role and enforce it as a
# view decorator so every protected view stays DRY.


def get_user_role(user):
    """
    Derive the user's effective role from their Django group membership.
    'admin' takes priority when a user belongs to multiple groups.

    Returns one of: 'admin' | 'salesperson' | 'stockmanager' | None
    """
    groups = user.groups.values_list('name', flat=True)
    if 'admin' in groups:
        return 'admin'
    elif 'salesperson' in groups:
        return 'salesperson'
    elif 'stockmanager' in groups:
        return 'stockmanager'
    return None  # User is authenticated but has no recognised role


def allowed_roles(roles, message=None):
    """
    View decorator factory that restricts access to users whose role is in `roles`.

    Unauthorised users are redirected to their own dashboard (not a generic 403)
    so they land somewhere useful rather than an error page.

    Usage:
        @login_required
        @allowed_roles(['admin', 'stockmanager'], message='Access denied.')
        def my_view(request): ...

    Args:
        roles:   A list, tuple, or set of allowed role strings.
        message: Optional flash error shown to the redirected user.
    """
    def decorator(view_func):
        #@wraps is to preserve information about the original function when you decorate it.
        @wraps(view_func)
        #allows a function to accept any number of named arguments.
        # This is necessary because different views have different URL parameters (e.g. pk for edits).
        def _wrapped(request, *args, **kwargs):
            role    = get_user_role(request.user)
            allowed = set(roles) if isinstance(roles, (list, tuple, set)) else {roles}

            if role not in allowed:
                # Show the optional denial message before redirecting
                if message:
                    messages.error(request, message)

                # Redirect to the user's own dashboard rather than a generic page
                if role == 'stockmanager':
                    return redirect('/dashboard/stockmanager/')
                if role == 'salesperson':
                    return redirect('/dashboard/salesperson/')
                return redirect('/dashboard/admin/')

# If all checks pass, call the original view and pass along the request and any arguments
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator



# PUBLIC VIEWS
# Accessible without authentication: landing page, login, and logout.


def index(request):
    """Render the public landing/home page."""
    return render(request, 'index.html')


def login_view(request):
    """
    Handle user authentication.

    GET:  Render the login form.
    POST: Validate credentials and redirect each role to its own dashboard.
          If a user authenticates but has no group, they are immediately logged
          out to prevent a broken session with no valid role.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        errors   = {}

        # Basic presence validation before hitting the database
        if not username:
            errors['username'] = 'Username is required.'
        if not password:
            errors['password'] = 'Password is required.'

        if errors:
            return render(request, 'login.html', {'errors': errors, 'form_data': {'username': username}})

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Redirect to the appropriate role dashboard
            if user.groups.filter(name='admin').exists():
                return redirect('/dashboard/admin/')
            elif user.groups.filter(name='salesperson').exists():
                return redirect('/dashboard/salesperson/')
            elif user.groups.filter(name='stockmanager').exists():
                return redirect('/dashboard/stockmanager/')
            else:
                # Authenticated but ungrouped — log out immediately to avoid limbo
                messages.error(request, 'No role assigned to this account.')
                logout(request)
                return render(request, 'login.html')
        else:
            # Use '__all__' key so the template renders this as a non-field (form-level) error
            # errors['__all__'] = 'Invalid username or password.'
            errors['general'] = 'Invalid username or password.'
            return render(request, 'login.html', {'errors': errors, 'form_data': {'username': username}})

    return render(request, 'login.html')


def logout_view(request):
    """Log the current user out and redirect to the login page."""
    logout(request)
    return redirect('/login/')



# DASHBOARDS
# Each role has its own dashboard view with metrics relevant to that role.
# Users who navigate to the wrong dashboard URL are silently redirected to
# their own, preventing information leakage across roles.


@login_required
def dashboard_admin(request):
    """
    Admin dashboard: business-wide overview.

    Displays today's sales, monthly revenue/cost/gross-profit, stock health,
    pending customer pickups, and total outstanding supplier credit.
    Gross profit uses the product's current unit_cost as the cost basis
    (not the historical cost at time of sale).
    """
    # Non-admins are silently sent to their own dashboard
    role = get_user_role(request.user)
    if role == 'salesperson':
        return redirect('/dashboard/salesperson/')
    if role == 'stockmanager':
        return redirect('/dashboard/stockmanager/')

    today      = timezone.now().date()
    this_month = timezone.now().month
    this_year  = timezone.now().year

    #  Inventory 
    total_stock = sum(p.quantity for p in Product.objects.all())
    low_stock   = Product.objects.filter(quantity__lt=10)  # threshold: < 10 units

    #  Today's sales 
    sales_today       = Sale.objects.filter(date__date=today)
    sales_today_total = sum(s.total_price for s in sales_today)
    sales_today_count = sales_today.count()

    #  Monthly financial summary 
    sales_month   = Sale.objects.filter(date__month=this_month, date__year=this_year)
    revenue_month = sum(s.total_price for s in sales_month)
    # Cost basis: current buying price × quantity sold (not historical cost)
    cost_month    = sum(s.product.unit_cost * s.quantity for s in sales_month)
    gross_profit  = revenue_month - cost_month

    #  Customer & deposit metrics 
    deposit_members = Customer.objects.count()
    pending_pickups = CustomerDeposit.objects.filter(status='ready_pickup').count()

    #  Supplier credit 
    suppliers             = Supplier.objects.all()
    supplier_credit_total = sum(s.credit_amount for s in suppliers)
    supplier_count        = suppliers.count()

    recent_sales = Sale.objects.order_by('-date')[:5]

    context = {
        'total_stock':          total_stock,
        'sales_today_total':    sales_today_total,
        'sales_today_count':    sales_today_count,
        'revenue_month':        revenue_month,
        'cost_month':           cost_month,
        'gross_profit':         gross_profit,
        'low_stock':            low_stock,
        'low_stock_count':      low_stock.count(),
        'deposit_members':      deposit_members,
        'pending_pickups':      pending_pickups,
        'supplier_credit_total': supplier_credit_total,
        'supplier_count':       supplier_count,
        'recent_sales':         recent_sales,
        'suppliers':            suppliers,
    }
    return render(request, 'dashboard_admin.html', context)


@login_required
def dashboard_salesperson(request):
    """
    Salesperson dashboard: daily sales and deposit activity.

    Shows today's sales totals, transport fees collected, deposits received,
    pending pickups that need attention, and newly registered customers.
    """
    role = get_user_role(request.user)
    if role == 'admin':
        return redirect('/dashboard/admin/')
    if role == 'stockmanager':
        return redirect('/dashboard/stockmanager/')

    today = timezone.now().date()

    #  Today's sales summary 
    sales_today       = Sale.objects.filter(date__date=today)
    sales_today_total = sum(s.total_price for s in sales_today)
    sales_today_count = sales_today.count()
    transport_today   = sum(s.transport_fee for s in sales_today)

    #  Today's deposit summary 
    deposits_today       = CustomerDeposit.objects.filter(date=today)
    deposits_today_total = sum(d.amount_deposited for d in deposits_today)
    deposits_today_count = deposits_today.count()

    #  Operational counts 
    total_stock     = Product.objects.filter(quantity__gt=0).count()  # products with stock
    new_customers   = Customer.objects.filter(registration_date=today).count()
    pending_pickups = CustomerDeposit.objects.filter(status='ready_pickup')
    pending_count   = pending_pickups.count()

    recent_sales = Sale.objects.order_by('-date')[:5]

    context = {
        'sales_today_total':    sales_today_total,
        'sales_today_count':    sales_today_count,
        'deposits_today_total': deposits_today_total,
        'deposits_today_count': deposits_today_count,
        'total_stock':          total_stock,
        'new_customers':        new_customers,
        'pending_pickups':      pending_pickups,
        'pending_count':        pending_count,
        'transport_today':      transport_today,
        'recent_sales':         recent_sales,
    }
    return render(request, 'dashboard_salesperson.html', context)


@login_required
def dashboard_stockmanager(request):
    """
    Stock manager dashboard: warehouse health overview.

    Breaks stock into three tiers (critical < 5, low 5–9, well-stocked ≥ 10),
    shows cost vs sell value gap (potential margin sitting in the warehouse),
    and summarises recent stock arrivals.
    """
    role = get_user_role(request.user)
    if role == 'admin':
        return redirect('/dashboard/admin/')
    if role == 'salesperson':
        return redirect('/dashboard/salesperson/')

    products  = Product.objects.all()
    suppliers = Supplier.objects.all()

    #  Stock health tiers 
    total_stock     = sum(p.quantity for p in products)
    critical_stock  = Product.objects.filter(quantity__lt=5)          # urgent reorder needed
    critical_count  = critical_stock.count()
    low_stock_count = Product.objects.filter(quantity__gte=5, quantity__lt=10).count()
    well_stocked    = Product.objects.filter(quantity__gte=10).count()

    #  Inventory valuation 
    # The difference between sell value and cost value is the potential gross margin
    # locked in current inventory — useful for cash-flow awareness.
    stock_cost_value = sum(p.unit_cost  * p.quantity for p in products)
    stock_sell_value = sum(p.unit_price * p.quantity for p in products)

    #  Supplier credit 
    supplier_credit_total = sum(s.credit_amount for s in suppliers)
    supplier_count        = suppliers.count()

    #  Recent arrivals 
    recent_arrivals    = StockArrival.objects.order_by('-date')[:5]
    week_ago           = timezone.now() - timezone.timedelta(days=7)
    arrivals_this_week = StockArrival.objects.filter(date__gte=week_ago).count()

    context = {
        'total_stock':          total_stock,
        'critical_count':       critical_count,
        'low_stock_count':      low_stock_count,
        'well_stocked':         well_stocked,
        'products':             products,
        'suppliers':            suppliers,
        'supplier_credit_total': supplier_credit_total,
        'supplier_count':       supplier_count,
        'stock_cost_value':     stock_cost_value,
        'stock_sell_value':     stock_sell_value,
        'recent_arrivals':      recent_arrivals,
        'arrivals_this_week':   arrivals_this_week,
        'critical_stock':       critical_stock,
    }
    return render(request, 'dashboard_stockmanager.html', context)



# STOCK MANAGEMENT
# Admins and stock managers can add, edit, and delete products.
# Salespersons have read-only access to product data (needed for making sales)
# but are blocked from all write operations here.


@login_required
def stock(request):
    """
    List all products and handle new stock arrivals.

    GET:  Render the stock list.
    POST: Validate and save a new product/top-up. If the product name already
          exists, its quantity is incremented (top-up) rather than creating a
          duplicate record. A StockArrival record is always written for audit.
    """
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to access stock management.')
        return redirect('/dashboard/salesperson/')

    products = Product.objects.all()

    if request.method == 'POST':
        # Collect raw form values
        product_name   = request.POST.get('product_name', '').strip()
        supplier_name  = request.POST.get('supplier_name', '').strip()
        quantity_raw   = request.POST.get('quantity', '')
        unit_cost_raw  = request.POST.get('unit_cost', '')
        unit_price_raw = request.POST.get('unit_price', '')
        arrival_date   = request.POST.get('date', '').strip()

        errors    = {}
        form_data = {
            'product_name':  product_name,
            'supplier_name': supplier_name,
            'quantity':      quantity_raw,
            'unit_cost':     unit_cost_raw,
            'unit_price':    unit_price_raw,
            'date':           arrival_date,
        }

        #  Field-level validation 
        if not product_name:
            errors['product_name'] = 'Product name is required.'
        if not supplier_name:
            errors['supplier_name'] = 'Supplier name is required.'
        if not arrival_date:
            errors['date'] = 'Arrival date is required.'

        quantity,   err = parse_positive_int(quantity_raw, 'Quantity')
        if err: errors['quantity'] = err

        unit_cost,  err = parse_positive_decimal(unit_cost_raw, 'Unit cost')
        if err: errors['unit_cost'] = err

        unit_price, err = parse_positive_decimal(unit_price_raw, 'Unit price')
        if err: errors['unit_price'] = err

        #  Cross-field validation: selling price must cover buying price 
        # Only runs when both fields individually parsed without error
        if not errors.get('unit_cost') and not errors.get('unit_price') and unit_price and unit_cost:
            if unit_price < unit_cost:
                errors['unit_price'] = 'Selling price cannot be less than buying price.'

        if errors:
            return render(request, 'stock.html', {
                'products': products, 'errors': errors, 'form_data': form_data,
            })

        #  Persist: top-up if product exists, create if new 
        product, _ = Product.objects.get_or_create(
            name=product_name,
            defaults={'unit_cost': unit_cost, 'unit_price': unit_price, 'quantity': 0}
        )
        # Always update prices to reflect the latest delivery cost
        product.unit_cost  = unit_cost
        product.unit_price = unit_price
        product.quantity  += quantity
        product.save()

        # get_or_create ensures the supplier exists without duplicating records
        supplier, _ = Supplier.objects.get_or_create(name=supplier_name, defaults={'phone': ''})

        # Immutable audit trail: one StockArrival per delivery
        StockArrival.objects.create(
            product=product, supplier=supplier,
            quantity_received=quantity, unit_cost=unit_cost, unit_price=unit_price,
        )

        messages.success(request, f'{product_name} stock saved successfully!')
        return redirect('stock')

    return render(request, 'stock.html', {'products': products})


@login_required
def stock_edit(request, pk):
    """
    Edit an existing product's name, prices, and/or quantity.

    Quantity min_value=0 is intentional: a product can be marked as out-of-stock
    (quantity=0) without deleting the record and losing its sales history.
    """
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

        errors    = {}
        form_data = {
            'name':       name,
            'unit_cost':  unit_cost_raw,
            'unit_price': unit_price_raw,
            'quantity':   quantity_raw,
        }

        if not name:
            errors['name'] = 'Product name is required.'

        # min_value=0: allows setting quantity to zero without deleting the product
        quantity,   err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err: errors['quantity'] = err

        unit_cost,  err = parse_positive_decimal(unit_cost_raw, 'Unit cost')
        if err: errors['unit_cost'] = err

        unit_price, err = parse_positive_decimal(unit_price_raw, 'Unit price')
        if err: errors['unit_price'] = err

        # Cross-field price guard (same rule as stock creation)
        if not errors.get('unit_cost') and not errors.get('unit_price') and unit_price and unit_cost:
            if unit_price < unit_cost:
                errors['unit_price'] = 'Selling price cannot be less than buying price.'

        if errors:
            return render(request, 'stock_edit.html', {
                'product': product, 'errors': errors, 'form_data': form_data,
            })

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
    """
    Permanently delete a product record.
    Note: this also cascades to related Sales/StockArrivals depending on model FK settings.
    """
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to delete stock.')
        return redirect('/dashboard/salesperson/')

    product = get_object_or_404(Product, id=pk)
    name = product.name
    product.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('stock')



# SALES
# Admins and salespersons can record, edit, and delete sales.
# Stock managers are blocked from all write operations.
# Every sale deducts from product.quantity; every delete restores it.


@login_required
def sales(request):
    """
    List all sales and record new ones.

    POST flow:
      1. Validate product selection, quantity, and optional delivery distance.
      2. Check that enough stock exists before committing.
      3. Create the Sale record (Sale.save() auto-calculates transport_fee).
      4. Decrement product.quantity to keep inventory accurate.
    """
    role     = get_user_role(request.user)
    sales_qs = Sale.objects.all().order_by('-date')
    products = Product.objects.all()

    if request.method == 'POST':
        # Stock managers cannot record sales
        if role == 'stockmanager':
            messages.error(request, 'You are not authorized to record sales.')
            return redirect('/dashboard/stockmanager/')

        product_id   = request.POST.get('product_id', '').strip()
        quantity_raw = request.POST.get('quantity', '')
        # Default distance to '0' when not supplied (in-store sale, no delivery)
        distance_raw = request.POST.get('distance_km', '0') or '0'
        sale_date_raw = request.POST.get('date', '').strip()

        errors    = {}
        form_data = {
            'product_id':  product_id,
            'quantity':    quantity_raw,
            'distance_km': distance_raw,
            'date':          sale_date_raw,
        }

        #  Field-level validation 
        if not product_id:
            errors['product_id'] = 'Please select a product.'

        quantity, err = parse_positive_int(quantity_raw, 'Quantity')
        if err: errors['quantity'] = err

        # min_value=0: distance 0 means in-store / no delivery charge
        distance, err = parse_positive_decimal(distance_raw, 'Distance', min_value=0)
        if err: errors['distance_km'] = err
        if not sale_date_raw:
            errors['date'] = 'Sale date is required.'
        else:
            try:
                sale_date = timezone.datetime.strptime(sale_date_raw, '%Y-%m-%d').date()
                if sale_date > timezone.now().date():
                    errors['date'] = 'Sale date cannot be in the future.'
            except ValueError:
                errors['date'] = 'Invalid date format. Use YYYY-MM-DD.'

        # Stock availability check 
        # Only runs after product_id and quantity have individually passed validation
        if not errors.get('product_id') and not errors.get('quantity'):
            product = get_object_or_404(Product, id=product_id)
            if quantity > product.quantity:
                errors['quantity'] = f'Not enough stock. Only {product.quantity} units available.'

        if errors:
            return render(request, 'sales.html', {
                'sales': sales_qs, 'products': products,
                'errors': errors, 'form_data': form_data,
            })

        # Persist sale and update inventory
        product     = get_object_or_404(Product, id=product_id)
        total_price = product.unit_price * quantity

        # transport_fee is computed inside Sale.save() based on distance & total_price
        Sale.objects.create(
            product=product,
            quantity=quantity,
            unit_price=product.unit_price,
            total_price=total_price,
            distance_km=distance,
        )
        product.quantity -= quantity
        product.save()

        messages.success(request, f'Sale recorded for {product.name}!')
        return redirect('sales')

    return render(request, 'sales.html', {'sales': sales_qs, 'products': products})


@login_required
def sales_edit(request, pk):
    """
    Edit an existing sale record.

    Stock adjustment logic:
    - If the same product is kept: net-adjust quantity (old qty added back, new qty deducted).
    - If the product changes: fully restore old product's stock, fully deduct from new product's stock.

    The available_stock ceiling is (current stock + original sale qty) to avoid a false
    'not enough stock' error when simply changing the quantity of the same product.
    """
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit sales.')
        return redirect('/dashboard/stockmanager/')

    sale     = get_object_or_404(Sale, id=pk)
    products = Product.objects.all()

    if request.method == 'POST':
        product_id   = request.POST.get('product_id', '').strip()
        quantity_raw = request.POST.get('quantity', '')
        distance_raw = request.POST.get('distance_km', '0') or '0'

        errors    = {}
        form_data = {
            'product_id':  product_id,
            'quantity':    quantity_raw,
            'distance_km': distance_raw,
        }

        if not product_id:
            errors['product_id'] = 'Please select a product.'

        quantity, err = parse_positive_int(quantity_raw, 'Quantity')
        if err: errors['quantity'] = err

        distance, err = parse_positive_decimal(distance_raw, 'Distance', min_value=0)
        if err: errors['distance_km'] = err

        # Stock check: add back the original qty to get the true available ceiling
        if not errors.get('product_id') and not errors.get('quantity'):
            product         = get_object_or_404(Product, id=product_id)
            available_stock = product.quantity + sale.quantity
            if quantity > available_stock:
                errors['quantity'] = f'Not enough stock. Only {available_stock} units available.'

        if errors:
            return render(request, 'sales_edit.html', {
                'sale': sale, 'products': products,
                'errors': errors, 'form_data': form_data,
            })

        product       = get_object_or_404(Product, id=product_id)
        total_price   = product.unit_price * quantity
        transport_fee = 0 if total_price >= 500000 and distance <= 10 else 30000

        # Inventory reconciliation 
        if sale.product != product:
            # Product changed: undo the original deduction, then apply the new one
            sale.product.quantity += sale.quantity
            sale.product.save()
            product.quantity -= quantity
        else:
            # Same product: net adjustment only (avoids double-counting)
            product.quantity += sale.quantity - quantity
        product.save()

        # Update the sale record with all new values
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
    """
    Delete a sale and restore the sold units back to product inventory.
    Inventory is always restored before the sale record is removed.
    """
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete sales.')
        return redirect('/dashboard/stockmanager/')

    sale    = get_object_or_404(Sale, id=pk)
    product = sale.product

    # Restore sold stock before deleting the sale record
    product.quantity += sale.quantity
    product.save()
    sale.delete()

    messages.success(request, 'Sale deleted and stock restored!')
    return redirect('sales')



# SUPPLIERS
# Track suppliers and their outstanding credit balances.
# Salespersons are blocked from all supplier management.


@login_required
def supplier_credit(request):
    """
    List suppliers with credit balances and add/update supplier records.

    Uses get_or_create so submitting the same supplier name is an update,
    not a duplicate. Credit amount represents money still owed to the supplier.
    """
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to access supplier credit.')
        return redirect('/dashboard/salesperson/')

    products  = Product.objects.all()
    suppliers = Supplier.objects.all()

    if request.method == 'POST':
        name         = request.POST.get('name', '').strip()
        phone        = request.POST.get('phone', '').strip()
        address      = request.POST.get('address', '').strip()
        product_id   = request.POST.get('product_id', '')
        quantity_raw = request.POST.get('quantity', '0') or '0'
        credit_raw   = request.POST.get('credit_amount', '')

        errors    = {}
        form_data = {
            'name': name, 'phone': phone, 'address': address,
            'product_id': product_id, 'quantity': quantity_raw, 'credit_amount': credit_raw,
        }

        if not name:
            errors['name'] = 'Supplier name is required.'

        # Phone is optional but must be valid if supplied
        if phone and not is_valid_ugandan_phone(phone):
            errors['phone'] = 'Enter a valid Ugandan phone number e.g. 0712345678.'

        # min_value=0: a brand-new supplier may have no outstanding balance yet
        credit_amount, err = parse_positive_decimal(credit_raw, 'Credit amount', min_value=0)
        if err: errors['credit_amount'] = err

        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err: errors['quantity'] = err

        if errors:
            return render(request, 'supplier_credit.html', {
                'suppliers': suppliers, 'products': products,
                'errors': errors, 'form_data': form_data,
            })

        # Resolve optional product FK (product_id may be empty string)
        product  = get_object_or_404(Product, id=product_id) if product_id else None

        supplier, created = Supplier.objects.get_or_create(
            name=name,
            defaults={
                'phone': phone, 'address': address,
                'product': product, 'quantity': quantity,
                'credit_amount': credit_amount,
            }
        )
        if not created:
            # Supplier already exists: overwrite all editable fields
            supplier.credit_amount = credit_amount
            supplier.phone         = phone
            supplier.address       = address
            supplier.product       = product
            supplier.quantity      = quantity
            supplier.save()

        messages.success(request, f'Supplier {name} credit saved!')
        return redirect('supplier_credit')

    # Summary stats for the GET view
    total_credit        = sum(s.credit_amount for s in suppliers)
    supplier_count      = suppliers.count()
    suppliers_with_debt = suppliers.filter(credit_amount__gt=0).count()

    return render(request, 'supplier_credit.html', {
        'suppliers':          suppliers,
        'total_credit':       total_credit,
        'supplier_count':     supplier_count,
        'suppliers_with_debt': suppliers_with_debt,
        'products':           products,
    })


@login_required
def supplier_edit(request, pk):
    """Edit an existing supplier's contact details, linked product, and credit balance."""
    role = get_user_role(request.user)
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
        product_id   = request.POST.get('product_id', '')

        errors    = {}
        form_data = {
            'name': name, 'phone': phone, 'address': address,
            'quantity': quantity_raw, 'credit_amount': credit_raw, 'product_id': product_id,
        }

        if not name:
            errors['name'] = 'Supplier name is required.'

        if phone and not is_valid_ugandan_phone(phone):
            errors['phone'] = 'Enter a valid Ugandan phone number e.g. 0712345678.'

        credit_amount, err = parse_positive_decimal(credit_raw, 'Credit amount', min_value=0)
        if err: errors['credit_amount'] = err

        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err: errors['quantity'] = err

        if errors:
            return render(request, 'supplier_edit.html', {
                'supplier': supplier, 'products': products,
                'errors': errors, 'form_data': form_data,
            })

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
    """Permanently remove a supplier record."""
    role = get_user_role(request.user)
    # Salespersons are blocked from all supplier management, including deletion.
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to delete suppliers.')
        return redirect('/dashboard/salesperson/')

# Deleting a supplier will cascade-delete related StockArrivals depending on model FK settings.
    supplier = get_object_or_404(Supplier, id=pk)
    name = supplier.name
    supplier.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('supplier_credit')




@login_required
def customer_registration(request):
    role = get_user_role(request.user)
    # Salespersons and stock managers are blocked from customer registration, as this is an admin-only function.
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to access customer registration.')
        return redirect('/dashboard/stockmanager/')

    customers = Customer.objects.all()

# The registration form is intentionally simple to minimize barriers to signing up new customers.
    if request.method == 'POST':
        full_name         = request.POST.get('full_name', '').strip()
        NIN               = request.POST.get('NIN', '').strip().upper()
        phone             = request.POST.get('phone', '').strip()
        employer          = request.POST.get('employer', '').strip()
        address           = request.POST.get('address', '').strip()
        preferred_product = request.POST.get('preferred_product', '').strip()
        sale_date_raw     = request.POST.get('date', '').strip()

        errors    = {}
        form_data = {
            'full_name': full_name, 'NIN': NIN, 'phone': phone,
            'employer': employer, 'address': address,
            'preferred_product': preferred_product, 'date': sale_date_raw,
        }

        if not full_name:
            errors['full_name'] = 'Full name is required.'

        if not NIN:
            errors['NIN'] = 'NIN is required.'
        elif not is_valid_nin(NIN):
            errors['NIN'] = 'Invalid NIN. Expected 14 alphanumeric characters e.g. CM20100012345678.'
        elif Customer.objects.filter(NIN=NIN).exists():
            errors['NIN'] = f'A customer with NIN {NIN} is already registered.'

        if not phone:
            errors['phone'] = 'Phone number is required.'
        elif not is_valid_ugandan_phone(phone):
            errors['phone'] = 'Enter a valid Ugandan phone number e.g. 0712345678.'

        if not employer:
            errors['employer'] = 'Employer / workplace is required.'

        if not preferred_product:
            errors['preferred_product'] = 'Please select a preferred product.'

        if not address:
            errors['address'] = 'Physical address is required.'

        reg_date = timezone.now().date()
        if not sale_date_raw:
            errors['date'] = 'Registration date is required.'
        else:
            try:
                reg_date = timezone.datetime.strptime(sale_date_raw, '%Y-%m-%d').date()
                if reg_date > timezone.now().date():
                    errors['date'] = 'Registration date cannot be in the future.'
            except ValueError:
                errors['date'] = 'Invalid date format.'

        if errors:
            return render(request, 'customer_registration.html', {
                'customers': customers, 'errors': errors, 'form_data': form_data,
            })

        Customer.objects.create(
            full_name=full_name, NIN=NIN, phone=phone,
            employer=employer, address=address,
            preferred_product=preferred_product,
            registration_date=reg_date,
        )
        messages.success(request, f'{full_name} registered successfully!')
        return redirect('customer_registration')

    return render(request, 'customer_registration.html', {'customers': customers})


@login_required
def customer_edit(request, pk):
    """
    Edit an existing customer record.

    NIN uniqueness check uses exclude(id=pk) so the customer's own NIN
    doesn't falsely trigger a duplicate error when other fields are changed.
    """
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit customers.')
        return redirect('/dashboard/stockmanager/')

    customer = get_object_or_404(Customer, id=pk)

    if request.method == 'POST':
        full_name         = request.POST.get('full_name', '').strip()
        NIN               = request.POST.get('NIN', '').strip().upper()
        phone             = request.POST.get('phone', '').strip()
        employer          = request.POST.get('employer', '').strip()
        address           = request.POST.get('address', '').strip()
        preferred_product = request.POST.get('preferred_product', '').strip()

        errors    = {}
        form_data = {
            'full_name': full_name, 'NIN': NIN, 'phone': phone,
            'employer': employer, 'address': address, 'preferred_product': preferred_product,
        }

        if not full_name:
            errors['full_name'] = 'Full name is required.'

        if not NIN:
            errors['NIN'] = 'NIN is required.'
        elif not is_valid_nin(NIN):
            errors['NIN'] = 'Invalid NIN format. Expected 14 alphanumeric characters.'
        elif Customer.objects.filter(NIN=NIN).exclude(id=pk).exists():
            # exclude(id=pk) prevents the customer's own unchanged NIN from triggering this
            errors['NIN'] = f'Another customer already has NIN {NIN}.'

        if not phone:
            errors['phone'] = 'Phone number is required.'
        elif not is_valid_ugandan_phone(phone):
            errors['phone'] = 'Enter a valid Ugandan phone number e.g. 0712345678.'

        if errors:
            return render(request, 'customer_edit.html', {
                'customer': customer, 'errors': errors, 'form_data': form_data,
            })

        customer.full_name         = full_name
        customer.NIN               = NIN
        customer.phone             = phone
        customer.employer          = employer
        customer.address           = address
        customer.preferred_product = preferred_product
        customer.save()
        messages.success(request, f'{customer.full_name} updated successfully!')
        return redirect('customer_registration')

    return render(request, 'customer_edit.html', {'customer': customer})


@login_required
def customer_delete(request, pk):
    """Permanently remove a customer record."""
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete customers.')
        return redirect('/dashboard/stockmanager/')

    customer = get_object_or_404(Customer, id=pk)
    name = customer.full_name
    customer.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('customer_registration')



# CUSTOMER DEPOSITS
# Customers pay deposits to reserve products for future pickup.
# Status lifecycle: active → ready_pickup → collected (forward-only).
# Stock managers cannot access this section.

@login_required
def customer_deposit(request):

    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to access customer deposits.')
        return redirect('/dashboard/stockmanager/')

    def build_groups():
        """Return deposits grouped by customer with aggregated totals."""
        all_deposits = CustomerDeposit.objects.select_related(
            'customer', 'product'
        ).order_by('customer__full_name', '-date')

        grouped = defaultdict(list)
        for d in all_deposits:
            grouped[d.customer].append(d)

        customer_groups = []
        for customer, dep_list in grouped.items():
            total_deposited   = sum(d.amount_deposited   for d in dep_list)
            total_paid_pickup = sum(d.amount_paid_on_pickup for d in dep_list)
            customer_groups.append({
                'customer':          customer,
                'deposits':          dep_list,
                'total_deposited':   total_deposited,
                'total_paid_pickup': total_paid_pickup,
                'remaining':         total_deposited - total_paid_pickup,
                'total_units':       sum(d.units_equivalent for d in dep_list),
            })
        return customer_groups

    if request.method == 'POST':
        nin            = request.POST.get('nin', '').strip()
        product_id     = request.POST.get('product_id', '')
        amount_raw     = request.POST.get('amount_deposited', '')
        payment_method = request.POST.get('payment_method', '').strip()
        payment_date   = request.POST.get('payment_date', '').strip()
        quantity_raw   = request.POST.get('quantity', '0') or '0'

        errors    = {}
        form_data = {
            'nin': nin, 'product_id': product_id, 'amount_deposited': amount_raw,
            'payment_method': payment_method, 'payment_date': payment_date, 'quantity': quantity_raw,
        }

        # Customer NIN
        if not nin:
            errors['nin'] = 'Customer NIN is required.'
        else:
            try:
                customer = Customer.objects.get(NIN=nin)
            except Customer.DoesNotExist:
                errors['nin'] = f'No customer found with NIN {nin}.'

        # Product
        if not product_id:
            errors['product_id'] = 'Please select a product.'

        # Amount
        if not amount_raw:
            errors['amount_deposited'] = 'Deposit amount is required.'
        else:
            amount_deposited, err = parse_positive_decimal(amount_raw, 'Deposit amount')
            if err: errors['amount_deposited'] = err

        # Payment method
        if not payment_method:
            errors['payment_method'] = 'Please select a payment method.'

        # Quantity
        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err: errors['quantity'] = err

        # Payment date (optional but validated if provided)
        parsed_date = timezone.now().date()
        if payment_date:
            try:
                parsed_date = timezone.datetime.strptime(payment_date, '%Y-%m-%d').date()
                if parsed_date > timezone.now().date():
                    errors['payment_date'] = 'Payment date cannot be in the future.'
            except ValueError:
                errors['payment_date'] = 'Invalid date format.'

        if errors:
            return render(request, 'customer_deposit.html', {
                'customer_groups': build_groups(),
                'products':        Product.objects.all(),
                'errors':          errors,
                'form_data':       form_data,
            })

        product = get_object_or_404(Product, id=product_id)
        CustomerDeposit.objects.create(
            customer=customer,
            product=product,
            amount_deposited=amount_deposited,
            unit_price=product.unit_price,
            quantity=quantity,
            payment_method=payment_method,
            date=parsed_date,
        )

        messages.success(
            request,
            f'Deposit of UGX {int(amount_deposited):,} recorded for {customer.full_name}!'
        )
        return redirect('customer_deposit')

    return render(request, 'customer_deposit.html', {
        'customer_groups': build_groups(),
        'products':        Product.objects.all(),
    })



@login_required
def deposit_edit(request, pk):
   
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit deposits.')
        return redirect('/dashboard/stockmanager/')

    deposit = get_object_or_404(CustomerDeposit, id=pk)

    if request.method == 'POST':
        new_status   = request.POST.get('status', deposit.status)
        pickup_raw   = request.POST.get('amount_paid_on_pickup', '0') or '0'
        # Default quantity to the existing value if not supplied
        quantity_raw = request.POST.get('quantity', str(deposit.quantity)) or str(deposit.quantity)

        errors    = {}
        form_data = {
            'status':               new_status,
            'amount_paid_on_pickup': pickup_raw,
            'quantity':             quantity_raw,
        }

        # Enforce the forward-only status progression
        STATUS_ORDER = ['active', 'ready_pickup', 'collected']
        if new_status not in STATUS_ORDER:
            errors['status'] = 'Invalid status selected.'
        elif STATUS_ORDER.index(new_status) < STATUS_ORDER.index(deposit.status):
            errors['status'] = f'Cannot revert status from "{deposit.status}" back to "{new_status}".'

        amount_paid, err = parse_positive_decimal(pickup_raw, 'Amount paid on pickup', min_value=0)
        if err: errors['amount_paid_on_pickup'] = err

        quantity, err = parse_positive_int(quantity_raw, 'Quantity', min_value=0)
        if err: errors['quantity'] = err

        if errors:
            return render(request, 'deposit_edit.html', {
                'deposit': deposit, 'errors': errors, 'form_data': form_data,
            })

        deposit.status                = new_status
        deposit.amount_paid_on_pickup = amount_paid
        deposit.quantity              = quantity
        # Explicit update_fields prevents accidental overwrite of the original deposit date
        deposit.save(update_fields=['status', 'amount_paid_on_pickup', 'quantity'])

        messages.success(request, 'Deposit updated successfully!')
        return redirect('customer_deposit')

    return render(request, 'deposit_edit.html', {'deposit': deposit})


@login_required
def deposit_delete(request, pk):
    """Permanently remove a deposit record."""
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete deposits.')
        return redirect('/dashboard/stockmanager/')

    deposit = get_object_or_404(CustomerDeposit, id=pk)
    deposit.delete()
    messages.success(request, 'Deposit deleted successfully!')
    return redirect('customer_deposit')



# SUPPLIER PAYMENTS
# Record partial or full payments against a supplier's outstanding credit.
# Restricted to admins and stock managers via the @allowed_roles decorator.


@login_required
@allowed_roles(['admin', 'stockmanager'], message='You are not authorized to access supplier payments.')
def supplier_pay(request, supplier_id):
    """
    Record a payment against a supplier's credit balance.

    Validation rules:
    - Amount must be a positive number.
    - Amount cannot exceed the supplier's current outstanding balance
      (prevents accidentally overpaying and going into negative credit).
    """
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        amount_raw = request.POST.get('amount_paid', '').strip()
        errors     = {}
        form_data  = {'amount_paid': amount_raw}

        try:
            amount_paid = Decimal(amount_raw)
        except InvalidOperation:
            errors['amount_paid'] = 'Enter a valid number.'
            return render(request, 'supplier_pay.html', {
                'supplier': supplier, 'errors': errors, 'form_data': form_data,
            })

        if amount_paid <= 0:
            errors['amount_paid'] = 'Amount must be greater than zero.'
        elif amount_paid > supplier.credit_amount:
            # Prevent overpayment that would push credit_amount below zero
            errors['amount_paid'] = (
                f'Amount exceeds outstanding balance of UGX {supplier.credit_amount:,.0f}.'
            )

        if errors:
            return render(request, 'supplier_pay.html', {
                'supplier': supplier, 'errors': errors, 'form_data': form_data,
            })

        supplier.credit_amount -= amount_paid
        supplier.save()
        messages.success(
            request,
            f'UGX {amount_paid:,.0f} paid. Remaining: UGX {supplier.credit_amount:,.0f}.'
        )
        return redirect('/supplier_credit/')

    return render(request, 'supplier_pay.html', {'supplier': supplier})



# RECEIPTS


@login_required
def sale_receipt(request, pk):
    """Render a printable receipt for the given sale."""
    sale = get_object_or_404(Sale, id=pk)
    return render(request, 'sale_receipt.html', {'sale': sale})



# DEPOSIT PAYMENTS
# Allow staff to record a cash payment against an existing deposit balance.
# When the balance reaches zero the deposit is automatically marked 'collected'.



def pay_deposit(request, deposit_id):
   
    deposit = get_object_or_404(CustomerDeposit, id=deposit_id)

    if request.method == 'POST':
        amount_raw     = request.POST.get('amount_paid', '').strip()
        payment_method = request.POST.get('payment_method', 'cash')
        payment_date   = request.POST.get('payment_date', '')

        errors    = {}
        form_data = {
            'amount_paid':    amount_raw,
            'payment_method': payment_method,
            'payment_date':   payment_date,
        }

        try:
            amount_paid = int(amount_raw)
            if amount_paid <= 0:
                errors['amount_paid'] = 'Payment amount must be greater than zero.'
            elif amount_paid > deposit.amount_deposited:
                # Prevent overpayment beyond the remaining deposit balance
                errors['amount_paid'] = (
                    f'Amount exceeds deposit balance of UGX {int(deposit.amount_deposited):,}.'
                )
        except (ValueError, TypeError):
            errors['amount_paid'] = 'Enter a valid whole number.'

        if errors:
            return render(request, 'pay_deposit.html', {
                'deposit': deposit, 'errors': errors, 'form_data': form_data,
            })

        deposit.amount_deposited -= amount_paid

        # Auto-close the deposit when the balance is fully cleared
        if deposit.amount_deposited <= 0:
            deposit.amount_deposited = 0
            deposit.status = 'collected'

        deposit.save()
        messages.success(
            request,
            f'Payment of UGX {amount_paid:,} recorded for {deposit.customer.full_name}.'
        )
        return redirect('/customer_deposit/')

    return render(request, 'pay_deposit.html', {'deposit': deposit})

@login_required
def customer_deposit_receipt(request, pk):
    deposit = get_object_or_404(CustomerDeposit, id=pk)

    context = {
        'deposit': deposit
    }

    return render(request, 'customer_deposit_receipt.html', context)

