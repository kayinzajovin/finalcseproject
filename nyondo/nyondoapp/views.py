# nyondoapp/views.py

# Django shortcut helpers for rendering, redirecting, and object lookup.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

# Django messages framework for user-facing success/error notifications.
from django.contrib import messages

# Django timezone utilities for date-aware queries.
from django.utils import timezone

# Django auth helpers for login, logout, and user authentication.


# Standard library utilities.
from functools import wraps
from decimal import Decimal
from collections import defaultdict

# Application models for ORM access.
from .models import Product, Supplier, Sale, CustomerDeposit, StockArrival, Customer

# HTTP response rendering and template helpers.
from django.http import HttpResponse
from django.template.loader import render_to_string

 


def index(request):
    # Simple view for the homepage using Django render shortcut.
    return render(request, 'index.html')
 
# def login_view(request):
#     # Handle login form submission and authenticate with Django auth.
#     # Uses django.contrib.auth.authenticate() and login() helpers.
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         role = request.POST.get('role')

#         # Check username and password against the Django user database.
#         user = authenticate(request, username=username, password=password)

#         if user is not None:
#             # get the groups this user belongs to
#             user_groups = user.groups.values_list('name', flat=True)

#             # check user belongs to the selected role group
#             if role == 'admin' and 'admin' in user_groups:
#                 login(request, user)
#                 return redirect('/dashboard/admin/')
#             elif role == 'salesperson' and 'salesperson' in user_groups:
#                 login(request, user)
#                 return redirect('/dashboard/salesperson/')
#             elif role == 'stockmanager' and 'stockmanager' in user_groups:
#                 login(request, user)
#                 return redirect('/dashboard/stockmanager/')
#             else:
#                 # user exists but wrong role selected
#                 messages.error(request, 'You are not authorized for that role.')
#                 return render(request, 'login.html')
#         else:
#             # wrong username or password
#             messages.error(request, 'Invalid username or password.')
#             return render(request, 'login.html')

#     return render(request, 'login.html')

def login_view(request):

    # check if the form was submitted
    if request.method == 'POST':

        # get username and password from the form
        username = request.POST.get('username')
        password = request.POST.get('password')

        # check if the username and password are correct
        user = authenticate(request, username=username, password=password)

        # if user exists
        if user is not None:

            # log the user into the system
            login(request, user)

            # check if user belongs to admin group
            if user.groups.filter(name='admin').exists():
                return redirect('/dashboard/admin/')

            # check if user belongs to salesperson group
            elif user.groups.filter(name='salesperson').exists():
                return redirect('/dashboard/salesperson/')

            # check if user belongs to stockmanager group
            elif user.groups.filter(name='stockmanager').exists():
                return redirect('/dashboard/stockmanager/')

            # if user has no group assigned
            else:
                messages.error(request, 'No role assigned to this account.')

                # log user out
                logout(request)

                return render(request, 'login.html')

        # if username or password is wrong
        else:
            messages.error(request, 'Invalid username or password.')

    # open login page
    return render(request, 'login.html')


def logout_view(request):
    # log the user out and redirect to login page
    logout(request)
    return redirect('/login/')


# helper function to get the role of the logged in user
#checks the groups the user belongs to and returns the role as a string

def get_user_role(user):
    groups = user.groups.values_list('name', flat=True)
    if 'admin' in groups:
        return 'admin'
    elif 'salesperson' in groups:
        return 'salesperson'
    elif 'stockmanager' in groups:
        return 'stockmanager'
    return None


def allowed_roles(roles, message=None):
    # Custom decorator to restrict a view to selected user role groups.
    # Uses Django messages and redirect helpers when access is denied.
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)
            allowed = set(roles) if isinstance(roles, (list, tuple, set)) else {roles}
            if role not in allowed:
                if message:
                    messages.error(request, message)
                if role == 'stockmanager':
                    return redirect('/dashboard/stockmanager/')
                if role == 'salesperson':
                    return redirect('/dashboard/salesperson/')
                return redirect('/dashboard/admin/')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


#user must be logged in to access any dashboard
@login_required
def dashboard_admin(request):
    # only admin can access this dashboard
    role = get_user_role(request.user)
    if role == 'salesperson':
        return redirect('/dashboard/salesperson/')
    if role == 'stockmanager':
        return redirect('/dashboard/stockmanager/')

    today = timezone.now().date()
    this_month = timezone.now().month
    this_year = timezone.now().year

    # total stock units across all products
    total_stock = sum(p.quantity for p in Product.objects.all())

    # sales made today
    sales_today = Sale.objects.filter(date__date=today)
    sales_today_total = sum(s.total_price for s in sales_today)
    sales_today_count = sales_today.count()

    # sales this month
    sales_month = Sale.objects.filter(date__month=this_month, date__year=this_year)
    revenue_month = sum(s.total_price for s in sales_month)

    # cost of goods sold this month
    cost_month = sum(s.unit_price * s.quantity for s in sales_month)

    # gross profit this month
    gross_profit = revenue_month - cost_month

    # low stock products — quantity less than 10
    low_stock = Product.objects.filter(quantity__lt=10)
    low_stock_count = low_stock.count()

    # deposit scheme members
    deposit_members = Customer.objects.count()

    # pending pickups
    pending_pickups = CustomerDeposit.objects.filter(status='ready_pickup').count()

    # supplier credit totals
    suppliers = Supplier.objects.all()
    supplier_credit_total = sum(s.credit_amount for s in suppliers)
    supplier_count = suppliers.count()

    # recent 5 sales
    recent_sales = Sale.objects.order_by('-date')[:5]

    context = {
        'total_stock': total_stock,
        'sales_today_total': sales_today_total,
        'sales_today_count': sales_today_count,
        'revenue_month': revenue_month,
        'cost_month': cost_month,
        'gross_profit': gross_profit,
        'low_stock': low_stock,
        'low_stock_count': low_stock_count,
        'deposit_members': deposit_members,
        'pending_pickups': pending_pickups,
        'supplier_credit_total': supplier_credit_total,
        'supplier_count': supplier_count,
        'recent_sales': recent_sales,
        'suppliers': suppliers,
    }
#
    return render(request, 'dashboard_admin.html', context)



@login_required
def dashboard_salesperson(request):
    # only salesperson can access this dashboard
    role = get_user_role(request.user)
    if role == 'admin':
        return redirect('/dashboard/admin/')
    if role == 'stockmanager':
        return redirect('/dashboard/stockmanager/')

    today = timezone.now().date()

    # sales made today
    sales_today = Sale.objects.filter(date__date=today)
    sales_today_total = sum(s.total_price for s in sales_today)
    sales_today_count = sales_today.count()

    # deposits today
    deposits_today = CustomerDeposit.objects.filter(date=today)
    deposits_today_total = sum(d.amount_deposited for d in deposits_today)
    deposits_today_count = deposits_today.count()

    # total stock items available
    total_stock = Product.objects.filter(quantity__gt=0).count()

    # new customers registered today
    new_customers = Customer.objects.filter(registration_date=today).count()

    # pending pickups
    pending_pickups = CustomerDeposit.objects.filter(status='ready_pickup')
    pending_count = pending_pickups.count()

    # transport charged today
    transport_today = sum(s.transport_fee for s in sales_today)

    # recent 5 sales
    recent_sales = Sale.objects.order_by('-date')[:5]

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
    # only stock manager can access this dashboard
    role = get_user_role(request.user)
    if role == 'admin':
        return redirect('/dashboard/admin/')
    if role == 'salesperson':
        return redirect('/dashboard/salesperson/')

    # total stock units across all products
    total_stock = sum(p.quantity for p in Product.objects.all())

    # critical stock — quantity less than 5
    critical_stock = Product.objects.filter(quantity__lt=5)
    critical_count = critical_stock.count()

    # low stock — quantity between 5 and 10
    low_stock_count = Product.objects.filter(quantity__gte=5, quantity__lt=10).count()

    # well stocked — quantity 10 and above
    well_stocked = Product.objects.filter(quantity__gte=10).count()

    # all products for stock level monitor
    products = Product.objects.all()

    # supplier credit totals
    suppliers = Supplier.objects.all()
    supplier_credit_total = sum(s.credit_amount for s in suppliers)
    supplier_count = suppliers.count()

    # stock value — cost and selling
    stock_cost_value = sum(p.unit_cost * p.quantity for p in products)
    stock_sell_value = sum(p.unit_price * p.quantity for p in products)

    # recent stock arrivals
    recent_arrivals = StockArrival.objects.order_by('-date')[:5]

    # arrivals this week
    week_ago = timezone.now() - timezone.timedelta(days=7)
    arrivals_this_week = StockArrival.objects.filter(date__gte=week_ago).count()

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


@login_required
def stock(request):
    # only admin and stock manager can access stock
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to access stock management.')
        return redirect('/dashboard/salesperson/')

    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        quantity = request.POST.get('quantity')
        unit_cost = request.POST.get('unit_cost')
        unit_price = request.POST.get('unit_price')
        supplier_name = request.POST.get('supplier_name')

        if not product_name or not quantity or not unit_cost or not unit_price or not supplier_name:
            messages.error(request, 'Please fill in all required fields before saving.')
            products = Product.objects.all()
            return render(request, 'stock.html', {'products': products})

        quantity = int(quantity)

        product, created = Product.objects.get_or_create(
            name=product_name,
            defaults={'unit_cost': unit_cost, 'unit_price': unit_price, 'quantity': 0}
        )

        product.unit_cost = unit_cost
        product.unit_price = unit_price
        product.quantity += quantity
        product.save()

        supplier, _ = Supplier.objects.get_or_create(
            name=supplier_name,
            defaults={'phone': ''}
        )

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
    # only admin and stock manager can edit stock
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to edit stock.')
        return redirect('/dashboard/salesperson/')

    product = Product.objects.get(id=pk)

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.unit_cost = request.POST.get('unit_cost')
        product.unit_price = request.POST.get('unit_price')
        product.quantity = request.POST.get('quantity')
        product.save()
        messages.success(request, f'{product.name} updated successfully!')
        return redirect('stock')

    return render(request, 'stock_edit.html', {'product': product})


@login_required
def stock_delete(request, pk):
    # only admin and stock manager can delete stock
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to delete stock.')
        return redirect('/dashboard/salesperson/')

    product = Product.objects.get(id=pk)
    name = product.name
    product.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('stock')


@login_required
def sales(request):
    # all roles can view sales but only admin and salesperson can record
    role = get_user_role(request.user)

    if request.method == 'POST' and role == 'stockmanager':
        messages.error(request, 'You are not authorized to record sales.')
        return redirect('/dashboard/stockmanager/')

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        distance_km = request.POST.get('distance_km', 0)

        if not product_id or not quantity:
            messages.error(request, 'Please select a product and enter quantity.')
            sales = Sale.objects.all().order_by('-date')
            products = Product.objects.all()
            return render(request, 'sales.html', {'sales': sales, 'products': products})

        quantity = int(quantity)
        product = Product.objects.get(id=product_id)

        if quantity > product.quantity:
            messages.error(request, f'Not enough stock. Only {product.quantity} units available.')
            sales = Sale.objects.all().order_by('-date')
            products = Product.objects.all()
            return render(request, 'sales.html', {'sales': sales, 'products': products})

        total_price = product.unit_price * quantity

        Sale.objects.create(
            product=product,
            quantity=quantity,
            unit_price=product.unit_price,
            total_price=total_price,
            distance_km=distance_km,
        )

        product.quantity -= quantity
        product.save()

        messages.success(request, f'Sale recorded for {product.name}!')
        return redirect('sales')

    sales = Sale.objects.all().order_by('-date')
    products = Product.objects.all()
    return render(request, 'sales.html', {'sales': sales, 'products': products})


@login_required
def sales_delete(request, pk):
    # only admin and salesperson can delete sales
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete sales.')
        return redirect('/dashboard/stockmanager/')

    sale = Sale.objects.get(id=pk)
    product = sale.product
    product.quantity += sale.quantity
    product.save()
    sale.delete()
    messages.success(request, 'Sale deleted and stock restored!')
    return redirect('sales')

@login_required
def sales_edit(request, pk):
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit sales.')
        return redirect('/dashboard/stockmanager/')

    sale = Sale.objects.get(id=pk)
    products = Product.objects.all()

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity'))
        distance_km = float(request.POST.get('distance_km') or 0)

        product = Product.objects.get(id=product_id)
        total_price = product.unit_price * quantity

        if distance_km > 0:
            transport_fee = 0 if total_price >= 500000 and distance_km <= 10 else 30000
        else:
            transport_fee = 0

        sale.product = product
        sale.quantity = quantity
        sale.unit_price = product.unit_price
        sale.total_price = total_price
        sale.transport_fee = transport_fee
        sale.grand_total = total_price + transport_fee
        sale.save()
        messages.success(request, 'Sale updated successfully!')
        return redirect('sales')

    return render(request, 'sales_edit.html', {'sale': sale, 'products': products})


@login_required
def supplier_credit(request):
    # only admin and stock manager can access supplier credit
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to access supplier credit.')
        return redirect('/dashboard/salesperson/')

    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity') or 0
        credit_amount = request.POST.get('credit_amount')

        products = Product.objects.all()

        if not name or not credit_amount:
            messages.error(request, 'Supplier name and credit amount are required.')
            suppliers = Supplier.objects.all()
            return render(request, 'supplier_credit.html', {
                'suppliers': suppliers,
                'products': products,
            })

        product = Product.objects.get(id=product_id) if product_id else None
        quantity = int(quantity)

        supplier, created = Supplier.objects.get_or_create(
            name=name,
            defaults={
                'phone': phone,
                'address': address,
                'product': product,
                'quantity': quantity,
                'credit_amount': credit_amount,
            }
        )

        if not created:
            supplier.credit_amount = credit_amount
            supplier.phone = phone
            supplier.address = address
            supplier.product = product
            supplier.quantity = quantity
            supplier.save()

        messages.success(request, f'Supplier {name} credit saved!')
        return redirect('supplier_credit')

    suppliers = Supplier.objects.all()
    total_credit = sum(s.credit_amount for s in suppliers)
    supplier_count = suppliers.count()
    suppliers_with_debt = suppliers.filter(credit_amount__gt=0).count()
    products = Product.objects.all()

    return render(request, 'supplier_credit.html', {
        'suppliers': suppliers,
        'total_credit': total_credit,
        'supplier_count': supplier_count,
        'suppliers_with_debt': suppliers_with_debt,
        'products': products,
    })


@login_required
def supplier_edit(request, pk):
    # only admin and stock manager can edit suppliers
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to edit suppliers.')
        return redirect('/dashboard/salesperson/')

    supplier = Supplier.objects.get(id=pk)

    if request.method == 'POST':
        supplier.name = request.POST.get('name')
        supplier.phone = request.POST.get('phone')
        supplier.address = request.POST.get('address')
        supplier.quantity = request.POST.get('quantity') or 0
        supplier.credit_amount = request.POST.get('credit_amount')
        product_id = request.POST.get('product_id')
        supplier.product = Product.objects.get(id=product_id) if product_id else None
        supplier.save()
        messages.success(request, f'{supplier.name} updated successfully!')
        return redirect('supplier_credit')

    products = Product.objects.all()
    return render(request, 'supplier_edit.html', {'supplier': supplier, 'products': products})


@login_required
def supplier_delete(request, pk):
    # only admin and stock manager can delete suppliers
    role = get_user_role(request.user)
    if role == 'salesperson':
        messages.error(request, 'You are not authorized to delete suppliers.')
        return redirect('/dashboard/salesperson/')

    supplier = Supplier.objects.get(id=pk)
    name = supplier.name
    supplier.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('supplier_credit')


@login_required
def customer_registration(request):
    # only admin and salesperson can access customer registration
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to access customer registration.')
        return redirect('/dashboard/stockmanager/')

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        NIN = request.POST.get('NIN')
        phone = request.POST.get('phone')
        employer = request.POST.get('employer')
        address = request.POST.get('address')
        preferred_product = request.POST.get('preferred_product')

        if not full_name or not NIN or not phone:
            messages.error(request, 'Full name, NIN and phone number are required.')
            customers = Customer.objects.all()
            return render(request, 'customer_registration.html', {'customers': customers})

        if Customer.objects.filter(NIN=NIN).exists():
            messages.error(request, f'A customer with NIN {NIN} is already registered.')
            customers = Customer.objects.all()
            return render(request, 'customer_registration.html', {'customers': customers})

        Customer.objects.create(
            full_name=full_name,
            NIN=NIN,
            phone=phone,
            employer=employer,
            address=address,
            preferred_product=preferred_product,
        )

        messages.success(request, f'{full_name} registered successfully!')
        return redirect('customer_registration')

    customers = Customer.objects.all()
    return render(request, 'customer_registration.html', {'customers': customers})


@login_required
def customer_edit(request, pk):
    # only admin and salesperson can edit customers
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit customers.')
        return redirect('/dashboard/stockmanager/')

    customer = Customer.objects.get(id=pk)

    if request.method == 'POST':
        customer.full_name = request.POST.get('full_name')
        customer.NIN = request.POST.get('NIN')
        customer.phone = request.POST.get('phone')
        customer.employer = request.POST.get('employer')
        customer.address = request.POST.get('address')
        customer.preferred_product = request.POST.get('preferred_product')
        customer.save()
        messages.success(request, f'{customer.full_name} updated successfully!')
        return redirect('customer_registration')

    return render(request, 'customer_edit.html', {'customer': customer})


@login_required
def customer_delete(request, pk):
    # only admin and salesperson can delete customers
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete customers.')
        return redirect('/dashboard/stockmanager/')

    customer = Customer.objects.get(id=pk)
    name = customer.full_name
    customer.delete()
    messages.success(request, f'{name} deleted successfully!')
    return redirect('customer_registration')



@login_required
def customer_deposit(request):
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to access customer deposits.')
        return redirect('/dashboard/stockmanager/')

    # helper: build customer_groups from all deposits ──────────────────
    def build_groups():
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
            remaining         = total_deposited - total_paid_pickup
            total_units       = sum(d.units_equivalent   for d in dep_list)

            customer_groups.append({
                'customer':          customer,
                'deposits':          dep_list,
                'total_deposited':   total_deposited,
                'total_paid_pickup': total_paid_pickup,
                'remaining':         remaining,
                'total_units':       total_units,
            })
        return customer_groups

    # POST: save a new deposit 
    if request.method == 'POST':
        nin              = request.POST.get('nin', '').strip()
        product_id       = request.POST.get('product_id')
        amount_deposited = request.POST.get('amount_deposited')
        payment_method   = request.POST.get('payment_method')
        payment_date     = request.POST.get('payment_date')

        # validate required fields
        if not nin or not product_id or not amount_deposited:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'customer_deposit.html', {
                'customer_groups': build_groups(),
                'products': Product.objects.all(),
            })

        # check customer exists
        try:
            customer = Customer.objects.get(NIN=nin)
        except Customer.DoesNotExist:
            messages.error(request, f'No customer found with NIN {nin}.')
            return render(request, 'customer_deposit.html', {
                'customer_groups': build_groups(),
                'products': Product.objects.all(),
            })

        product = Product.objects.get(id=product_id)

        quantity_str = request.POST.get('quantity', '0') or '0'
        try:
            quantity = int(quantity_str)
        except ValueError:
            quantity = 0

        # create the deposit record
        deposit = CustomerDeposit.objects.create(
            customer=customer,
            product=product,
            amount_deposited=amount_deposited,
            unit_price=product.unit_price,
            quantity=quantity,
            payment_method=payment_method,
        )

        # set payment date if provided
        if payment_date:
            deposit.date = payment_date
            deposit.save()

        messages.success(request, f'Deposit of UGX {int(float(amount_deposited)):,} recorded for {customer.full_name}!')
        return redirect('customer_deposit')

    # GET: show the page 
    return render(request, 'customer_deposit.html', {
        'customer_groups': build_groups(),
        'products': Product.objects.all(),
    })


@login_required
def deposit_edit(request, pk):
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit deposits.')
        return redirect('/dashboard/stockmanager/')

    deposit = get_object_or_404(CustomerDeposit, id=pk)

    if request.method == 'POST':
        deposit.status                = request.POST.get('status')
        deposit.amount_paid_on_pickup = request.POST.get('amount_paid_on_pickup', 0) or 0
        quantity_str                  = request.POST.get('quantity', deposit.quantity) or deposit.quantity
        try:
            deposit.quantity = int(quantity_str)
        except (ValueError, TypeError):
            deposit.quantity = deposit.quantity

        # only update these fields — never touch date
        deposit.save(update_fields=['status', 'amount_paid_on_pickup', 'quantity'])

        messages.success(request, 'Deposit updated successfully!')
        return redirect('customer_deposit')

    return render(request, 'deposit_edit.html', {'deposit': deposit})


@login_required
def deposit_delete(request, pk):
    # only admin and salesperson can delete deposits
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to delete deposits.')
        return redirect('/dashboard/stockmanager/')

    deposit = CustomerDeposit.objects.get(id=pk)
    deposit.delete()
    messages.success(request, 'Deposit deleted successfully!')
    return redirect('customer_deposit')



@login_required
@allowed_roles(['admin', 'stockmanager'], message='You are not authorized to access supplier payments.')
def supplier_pay(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        try:
            amount_paid = Decimal(request.POST.get('amount_paid', 0))
        except:
            messages.error(request, "Invalid amount entered.")
            return redirect(f'/supplier_credit/pay/{supplier_id}/')

        if amount_paid <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect(f'/supplier_credit/pay/{supplier_id}/')
        elif amount_paid > supplier.credit_amount:
            messages.error(request, f"Amount exceeds balance of UGX {supplier.credit_amount:,.0f}.")
            return redirect(f'/supplier_credit/pay/{supplier_id}/')
        else:
            supplier.credit_amount -= amount_paid
            supplier.save()
            messages.success(request, f"UGX {amount_paid:,.0f} paid. Remaining balance: UGX {supplier.credit_amount:,.0f}.")
            return redirect('/supplier_credit/')

    # GET — show the payment form
    return render(request, 'supplier_pay.html', {'supplier': supplier})

@login_required
def sale_receipt(request, pk):
    # get the sale and display a printable receipt
    sale = Sale.objects.get(id=pk)
    return render(request, 'sale_receipt.html', {'sale': sale})

