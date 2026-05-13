# from django.shortcuts import render, redirect
# from django.contrib import messages
# from django.utils import timezone
# from .models import Product, Supplier, Sale, CustomerDeposit, StockArrival, Customer
# from django.contrib.auth import authenticate, login, logout
# from django.contrib.auth.decorators import login_required


# def index(request):
#     return render(request, 'index.html')


# def login_view(request):
#     # handle login form submission
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         role = request.POST.get('role')

#         # check username and password against database
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


# def logout_view(request):
#     # log the user out and redirect to login page
#     logout(request)
#     return redirect('/login/')


# @login_required(login_url='/login/')
# def dashboard_admin(request):
#     today = timezone.now().date()
#     this_month = timezone.now().month
#     this_year = timezone.now().year

#     # total stock units across all products
#     total_stock = sum(p.quantity for p in Product.objects.all())

#     # sales made today
#     sales_today = Sale.objects.filter(date__date=today)
#     sales_today_total = sum(s.total_price for s in sales_today)
#     sales_today_count = sales_today.count()

#     # sales this month
#     sales_month = Sale.objects.filter(date__month=this_month, date__year=this_year)
#     revenue_month = sum(s.total_price for s in sales_month)

#     # cost of goods sold this month
#     cost_month = sum(s.unit_price * s.quantity for s in sales_month)

#     # gross profit this month
#     gross_profit = revenue_month - cost_month

#     # low stock products — quantity less than 10
#     low_stock = Product.objects.filter(quantity__lt=10)
#     low_stock_count = low_stock.count()

#     # deposit scheme members
#     deposit_members = Customer.objects.count()

#     # pending pickups
#     pending_pickups = CustomerDeposit.objects.filter(status='ready_pickup').count()

#     # supplier credit totals
#     suppliers = Supplier.objects.all()
#     supplier_credit_total = sum(s.credit_amount for s in suppliers)
#     supplier_count = suppliers.count()

#     # recent 5 sales
#     recent_sales = Sale.objects.order_by('-date')[:5]

#     context = {
#         'total_stock': total_stock,
#         'sales_today_total': sales_today_total,
#         'sales_today_count': sales_today_count,
#         'revenue_month': revenue_month,
#         'cost_month': cost_month,
#         'gross_profit': gross_profit,
#         'low_stock': low_stock,
#         'low_stock_count': low_stock_count,
#         'deposit_members': deposit_members,
#         'pending_pickups': pending_pickups,
#         'supplier_credit_total': supplier_credit_total,
#         'supplier_count': supplier_count,
#         'recent_sales': recent_sales,
#         'suppliers': suppliers,
#     }

#     return render(request, 'dashboard_admin.html', context)


# @login_required(login_url='/login/')
# def dashboard_salesperson(request):
#     return render(request, 'dashboard_salesperson.html')


# @login_required(login_url='/login/')
# def dashboard_stockmanager(request):
#     # total stock units across all products
#     total_stock = sum(p.quantity for p in Product.objects.all())

#     # critical stock — quantity less than 5
#     critical_stock = Product.objects.filter(quantity__lt=5)
#     critical_count = critical_stock.count()

#     # low stock — quantity between 5 and 10
#     low_stock_count = Product.objects.filter(quantity__gte=5, quantity__lt=10).count()

#     # well stocked — quantity 10 and above
#     well_stocked = Product.objects.filter(quantity__gte=10).count()

#     # all products for stock level monitor
#     products = Product.objects.all()

#     # supplier credit totals
#     suppliers = Supplier.objects.all()
#     supplier_credit_total = sum(s.credit_amount for s in suppliers)
#     supplier_count = suppliers.count()

#     # stock value — cost and selling
#     stock_cost_value = sum(p.unit_cost * p.quantity for p in products)
#     stock_sell_value = sum(p.unit_price * p.quantity for p in products)

#     # recent stock arrivals
#     recent_arrivals = StockArrival.objects.order_by('-date')[:5]

#     # arrivals this week
#     week_ago = timezone.now() - timezone.timedelta(days=7)
#     arrivals_this_week = StockArrival.objects.filter(date__gte=week_ago).count()

#     context = {
#         'total_stock': total_stock,
#         'critical_count': critical_count,
#         'low_stock_count': low_stock_count,
#         'well_stocked': well_stocked,
#         'products': products,
#         'suppliers': suppliers,
#         'supplier_credit_total': supplier_credit_total,
#         'supplier_count': supplier_count,
#         'stock_cost_value': stock_cost_value,
#         'stock_sell_value': stock_sell_value,
#         'recent_arrivals': recent_arrivals,
#         'arrivals_this_week': arrivals_this_week,
#         'critical_stock': critical_stock,
#     }

#     return render(request, 'dashboard_stockmanager.html', context)


# @login_required(login_url='/login/')
# def stock(request):
#     # handle form submission when new stock arrives
#     if request.method == 'POST':
#         product_name = request.POST.get('product_name')
#         quantity = request.POST.get('quantity')
#         unit_cost = request.POST.get('unit_cost')
#         unit_price = request.POST.get('unit_price')
#         supplier_name = request.POST.get('supplier_name')

#         # check all required fields are filled before saving
#         if not product_name or not quantity or not unit_cost or not unit_price or not supplier_name:
#             messages.error(request, 'Please fill in all required fields before saving.')
#             products = Product.objects.all()
#             return render(request, 'stock.html', {'products': products})

#         quantity = int(quantity)

#         # get the product if it exists, or create it if its new
#         product, created = Product.objects.get_or_create(
#             name=product_name,
#             defaults={'unit_cost': unit_cost, 'unit_price': unit_price, 'quantity': 0}
#         )

#         # always update cost and selling price with the latest arrival values
#         product.unit_cost = unit_cost
#         product.unit_price = unit_price
#         product.quantity += quantity  # add new stock to existing quantity
#         product.save()

#         # get the supplier if they exist, or create them if new
#         supplier, _ = Supplier.objects.get_or_create(
#             name=supplier_name,
#             defaults={'phone': ''}
#         )

#         # record this stock arrival in the database
#         StockArrival.objects.create(
#             product=product,
#             supplier=supplier,
#             quantity_received=quantity,
#             unit_cost=unit_cost,
#             unit_price=unit_price,
#         )

#         messages.success(request, f'{product_name} stock saved successfully!')
#         return redirect('stock')

#     # load all products to show in the stock table
#     products = Product.objects.all()
#     return render(request, 'stock.html', {'products': products})


# @login_required(login_url='/login/')
# def stock_edit(request, pk):
#     # get the product to edit
#     product = Product.objects.get(id=pk)

#     if request.method == 'POST':
#         # update product with new values from form
#         product.name = request.POST.get('name')
#         product.unit_cost = request.POST.get('unit_cost')
#         product.unit_price = request.POST.get('unit_price')
#         product.quantity = request.POST.get('quantity')
#         product.save()
#         messages.success(request, f'{product.name} updated successfully!')
#         return redirect('stock')

#     return render(request, 'stock_edit.html', {'product': product})


# @login_required(login_url='/login/')
# def stock_delete(request, pk):
#     # get the product and delete it
#     product = Product.objects.get(id=pk)
#     name = product.name
#     product.delete()
#     messages.success(request, f'{name} deleted successfully!')
#     return redirect('stock')


# @login_required(login_url='/login/')
# def sales(request):
#     # handle new sale form submission
#     if request.method == 'POST':
#         product_id = request.POST.get('product_id')
#         quantity = request.POST.get('quantity')
#         distance_km = request.POST.get('distance_km', 0)

#         # check all required fields are filled before saving
#         if not product_id or not quantity:
#             messages.error(request, 'Please select a product and enter quantity.')
#             sales = Sale.objects.all().order_by('-date')
#             products = Product.objects.all()
#             return render(request, 'sales.html', {'sales': sales, 'products': products})

#         quantity = int(quantity)

#         # get the product being sold
#         product = Product.objects.get(id=product_id)

#         # check there is enough stock before recording the sale
#         if quantity > product.quantity:
#             messages.error(request, f'Not enough stock. Only {product.quantity} units available.')
#             sales = Sale.objects.all().order_by('-date')
#             products = Product.objects.all()
#             return render(request, 'sales.html', {'sales': sales, 'products': products})

#         total_price = product.unit_price * quantity

#         # save the sale — transport fee is auto-calculated inside the Sale model
#         Sale.objects.create(
#             product=product,
#             quantity=quantity,
#             unit_price=product.unit_price,
#             total_price=total_price,
#             distance_km=distance_km,
#         )

#         # reduce stock quantity after sale
#         product.quantity -= quantity
#         product.save()

#         messages.success(request, f'Sale recorded for {product.name}!')
#         return redirect('sales')

#     # load all sales and products for the sales page
#     sales = Sale.objects.all().order_by('-date')
#     products = Product.objects.all()
#     return render(request, 'sales.html', {'sales': sales, 'products': products})


# @login_required(login_url='/login/')
# def sales_delete(request, pk):
#     # get the sale, restore stock quantity then delete
#     sale = Sale.objects.get(id=pk)
#     product = sale.product
#     product.quantity += sale.quantity  # restore stock when sale is deleted
#     product.save()
#     sale.delete()
#     messages.success(request, 'Sale deleted and stock restored!')
#     return redirect('sales')


# @login_required(login_url='/login/')
# def supplier_credit(request):
#     # handle new supplier credit form submission
#     if request.method == 'POST':
#         name = request.POST.get('name')
#         phone = request.POST.get('phone')
#         address = request.POST.get('address')
#         credit_amount = request.POST.get('credit_amount')

#         # check required fields are filled
#         if not name or not credit_amount:
#             messages.error(request, 'Supplier name and credit amount are required.')
#             suppliers = Supplier.objects.all()
#             return render(request, 'supplier_credit.html', {'suppliers': suppliers})

#         # get supplier if they exist, or create them if new
#         supplier, created = Supplier.objects.get_or_create(
#             name=name,
#             defaults={'phone': phone, 'address': address, 'credit_amount': credit_amount}
#         )

#         if not created:
#             # update credit amount and phone for existing supplier
#             supplier.credit_amount = credit_amount
#             supplier.phone = phone
#             supplier.save()

#         messages.success(request, f'Supplier {name} credit saved!')
#         return redirect('supplier_credit')

#     # load all suppliers and calculate summary totals
#     suppliers = Supplier.objects.all()
#     total_credit = sum(s.credit_amount for s in suppliers)
#     supplier_count = suppliers.count()
#     suppliers_with_debt = suppliers.filter(credit_amount__gt=0).count()

#     return render(request, 'supplier_credit.html', {
#         'suppliers': suppliers,
#         'total_credit': total_credit,
#         'supplier_count': supplier_count,
#         'suppliers_with_debt': suppliers_with_debt,
#     })


# @login_required(login_url='/login/')
# def supplier_edit(request, pk):
#     # get the supplier to edit
#     supplier = Supplier.objects.get(id=pk)

#     if request.method == 'POST':
#         supplier.name = request.POST.get('name')
#         supplier.phone = request.POST.get('phone')
#         supplier.address = request.POST.get('address')
#         supplier.credit_amount = request.POST.get('credit_amount')
#         supplier.save()
#         messages.success(request, f'{supplier.name} updated successfully!')
#         return redirect('supplier_credit')

#     return render(request, 'supplier_edit.html', {'supplier': supplier})


# @login_required(login_url='/login/')
# def supplier_delete(request, pk):
#     # get the supplier and delete them
#     supplier = Supplier.objects.get(id=pk)
#     name = supplier.name
#     supplier.delete()
#     messages.success(request, f'{name} deleted successfully!')
#     return redirect('supplier_credit')


# @login_required(login_url='/login/')
# def customer_registration(request):
#     # handle new customer registration form submission
#     if request.method == 'POST':
#         full_name = request.POST.get('full_name')
#         NIN = request.POST.get('NIN')
#         phone = request.POST.get('phone')
#         employer = request.POST.get('employer')
#         address = request.POST.get('address')
#         preferred_product = request.POST.get('preferred_product')

#         # check required fields are filled
#         if not full_name or not NIN or not phone:
#             messages.error(request, 'Full name, NIN and phone number are required.')
#             customers = Customer.objects.all()
#             return render(request, 'customer_registration.html', {'customers': customers})

#         # check NIN is not already registered
#         if Customer.objects.filter(NIN=NIN).exists():
#             messages.error(request, f'A customer with NIN {NIN} is already registered.')
#             customers = Customer.objects.all()
#             return render(request, 'customer_registration.html', {'customers': customers})

#         # save the new customer to the database
#         Customer.objects.create(
#             full_name=full_name,
#             NIN=NIN,
#             phone=phone,
#             employer=employer,
#             address=address,
#             preferred_product=preferred_product,
#         )

#         messages.success(request, f'{full_name} registered successfully!')
#         return redirect('customer_registration')

#     # load all registered customers to show in the table
#     customers = Customer.objects.all()
#     return render(request, 'customer_registration.html', {'customers': customers})


# @login_required(login_url='/login/')
# def customer_edit(request, pk):
#     # get the customer to edit
#     customer = Customer.objects.get(id=pk)

#     if request.method == 'POST':
#         customer.full_name = request.POST.get('full_name')
#         customer.NIN = request.POST.get('NIN')
#         customer.phone = request.POST.get('phone')
#         customer.employer = request.POST.get('employer')
#         customer.address = request.POST.get('address')
#         customer.preferred_product = request.POST.get('preferred_product')
#         customer.save()
#         messages.success(request, f'{customer.full_name} updated successfully!')
#         return redirect('customer_registration')

#     return render(request, 'customer_edit.html', {'customer': customer})


# @login_required(login_url='/login/')
# def customer_delete(request, pk):
#     # get the customer and delete them
#     customer = Customer.objects.get(id=pk)
#     name = customer.full_name
#     customer.delete()
#     messages.success(request, f'{name} deleted successfully!')
#     return redirect('customer_registration')


# @login_required(login_url='/login/')
# def customer_deposit(request):
#     # handle new deposit payment form submission
#     if request.method == 'POST':
#         nin = request.POST.get('nin')
#         product_id = request.POST.get('product_id')
#         amount_deposited = request.POST.get('amount_deposited')
#         payment_method = request.POST.get('payment_method')

#         # check required fields are filled
#         if not nin or not product_id or not amount_deposited:
#             messages.error(request, 'Please fill in all required fields.')
#             deposits = CustomerDeposit.objects.all().order_by('-date')
#             customers = Customer.objects.all()
#             products = Product.objects.all()
#             return render(request, 'customer_deposit.html', {
#                 'deposits': deposits,
#                 'customers': customers,
#                 'products': products,
#             })

#         # check customer exists by NIN
#         if not Customer.objects.filter(NIN=nin).exists():
#             messages.error(request, f'No customer found with NIN {nin}.')
#             deposits = CustomerDeposit.objects.all().order_by('-date')
#             customers = Customer.objects.all()
#             products = Product.objects.all()
#             return render(request, 'customer_deposit.html', {
#                 'deposits': deposits,
#                 'customers': customers,
#                 'products': products,
#             })

#         # find the customer by their NIN number
#         customer = Customer.objects.get(NIN=nin)
#         product = Product.objects.get(id=product_id)

#         # save the deposit — units equivalent is auto-calculated in the model
#         CustomerDeposit.objects.create(
#             customer=customer,
#             product=product,
#             amount_deposited=amount_deposited,
#             unit_price=product.unit_price,
#             payment_method=payment_method,
#         )

#         messages.success(request, f'Deposit recorded for {customer.full_name}!')
#         return redirect('customer_deposit')

#     # load all deposits, customers and products for the deposit page
#     deposits = CustomerDeposit.objects.all().order_by('-date')
#     customers = Customer.objects.all()
#     products = Product.objects.all()
#     return render(request, 'customer_deposit.html', {
#         'deposits': deposits,
#         'customers': customers,
#         'products': products,
#     })


# @login_required(login_url='/login/')
# def deposit_edit(request, pk):
#     # get the deposit to edit — mainly to update its status
#     deposit = CustomerDeposit.objects.get(id=pk)

#     if request.method == 'POST':
#         deposit.status = request.POST.get('status')
#         deposit.save()
#         messages.success(request, 'Deposit status updated successfully!')
#         return redirect('customer_deposit')

#     return render(request, 'deposit_edit.html', {'deposit': deposit})


# @login_required(login_url='/login/')
# def deposit_delete(request, pk):
#     # get the deposit and delete it
#     deposit = CustomerDeposit.objects.get(id=pk)
#     deposit.delete()
#     messages.success(request, 'Deposit deleted successfully!')
#     return redirect('customer_deposit')


from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Product, Supplier, Sale, CustomerDeposit, StockArrival, Customer
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


# helper function to get the role of the logged in user
def get_user_role(user):
    groups = user.groups.values_list('name', flat=True)
    if 'admin' in groups:
        return 'admin'
    elif 'salesperson' in groups:
        return 'salesperson'
    elif 'stockmanager' in groups:
        return 'stockmanager'
    return None


def index(request):
    return render(request, 'index.html')


def login_view(request):
    # handle login form submission
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')

        # check username and password against database
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # get the groups this user belongs to
            user_groups = user.groups.values_list('name', flat=True)

            # check user belongs to the selected role group
            if role == 'admin' and 'admin' in user_groups:
                login(request, user)
                return redirect('/dashboard/admin/')
            elif role == 'salesperson' and 'salesperson' in user_groups:
                login(request, user)
                return redirect('/dashboard/salesperson/')
            elif role == 'stockmanager' and 'stockmanager' in user_groups:
                login(request, user)
                return redirect('/dashboard/stockmanager/')
            else:
                # user exists but wrong role selected
                messages.error(request, 'You are not authorized for that role.')
                return render(request, 'login.html')
        else:
            # wrong username or password
            messages.error(request, 'Invalid username or password.')
            return render(request, 'login.html')

    return render(request, 'login.html')


def logout_view(request):
    # log the user out and redirect to login page
    logout(request)
    return redirect('/login/')


@login_required(login_url='/login/')
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

    return render(request, 'dashboard_admin.html', context)


@login_required(login_url='/login/')
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
    deposits_today = CustomerDeposit.objects.filter(date__date=today)
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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
        credit_amount = request.POST.get('credit_amount')

        if not name or not credit_amount:
            messages.error(request, 'Supplier name and credit amount are required.')
            suppliers = Supplier.objects.all()
            return render(request, 'supplier_credit.html', {'suppliers': suppliers})

        supplier, created = Supplier.objects.get_or_create(
            name=name,
            defaults={'phone': phone, 'address': address, 'credit_amount': credit_amount}
        )

        if not created:
            supplier.credit_amount = credit_amount
            supplier.phone = phone
            supplier.save()

        messages.success(request, f'Supplier {name} credit saved!')
        return redirect('supplier_credit')

    suppliers = Supplier.objects.all()
    total_credit = sum(s.credit_amount for s in suppliers)
    supplier_count = suppliers.count()
    suppliers_with_debt = suppliers.filter(credit_amount__gt=0).count()

    return render(request, 'supplier_credit.html', {
        'suppliers': suppliers,
        'total_credit': total_credit,
        'supplier_count': supplier_count,
        'suppliers_with_debt': suppliers_with_debt,
    })


@login_required(login_url='/login/')
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
        supplier.credit_amount = request.POST.get('credit_amount')
        supplier.save()
        messages.success(request, f'{supplier.name} updated successfully!')
        return redirect('supplier_credit')

    return render(request, 'supplier_edit.html', {'supplier': supplier})


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
def customer_deposit(request):
    # only admin and salesperson can access customer deposits
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to access customer deposits.')
        return redirect('/dashboard/stockmanager/')

    if request.method == 'POST':
        nin = request.POST.get('nin')
        product_id = request.POST.get('product_id')
        amount_deposited = request.POST.get('amount_deposited')
        payment_method = request.POST.get('payment_method')

        if not nin or not product_id or not amount_deposited:
            messages.error(request, 'Please fill in all required fields.')
            deposits = CustomerDeposit.objects.all().order_by('-date')
            customers = Customer.objects.all()
            products = Product.objects.all()
            return render(request, 'customer_deposit.html', {
                'deposits': deposits,
                'customers': customers,
                'products': products,
            })

        if not Customer.objects.filter(NIN=nin).exists():
            messages.error(request, f'No customer found with NIN {nin}.')
            deposits = CustomerDeposit.objects.all().order_by('-date')
            customers = Customer.objects.all()
            products = Product.objects.all()
            return render(request, 'customer_deposit.html', {
                'deposits': deposits,
                'customers': customers,
                'products': products,
            })

        customer = Customer.objects.get(NIN=nin)
        product = Product.objects.get(id=product_id)

        CustomerDeposit.objects.create(
            customer=customer,
            product=product,
            amount_deposited=amount_deposited,
            unit_price=product.unit_price,
            payment_method=payment_method,
        )

        messages.success(request, f'Deposit recorded for {customer.full_name}!')
        return redirect('customer_deposit')

    deposits = CustomerDeposit.objects.all().order_by('-date')
    customers = Customer.objects.all()
    products = Product.objects.all()
    return render(request, 'customer_deposit.html', {
        'deposits': deposits,
        'customers': customers,
        'products': products,
    })


@login_required(login_url='/login/')
def deposit_edit(request, pk):
    # only admin and salesperson can edit deposits
    role = get_user_role(request.user)
    if role == 'stockmanager':
        messages.error(request, 'You are not authorized to edit deposits.')
        return redirect('/dashboard/stockmanager/')

    deposit = CustomerDeposit.objects.get(id=pk)

    if request.method == 'POST':
        deposit.status = request.POST.get('status')
        deposit.save()
        messages.success(request, 'Deposit status updated successfully!')
        return redirect('customer_deposit')

    return render(request, 'deposit_edit.html', {'deposit': deposit})


@login_required(login_url='/login/')
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