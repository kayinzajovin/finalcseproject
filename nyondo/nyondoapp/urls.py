from django.urls import path
from . import views


urlpatterns = [
    # main pages
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # dashboard routes protected by login and role logic
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/salesperson/', views.dashboard_salesperson, name='dashboard_salesperson'),
    path('dashboard/stockmanager/', views.dashboard_stockmanager, name='dashboard_stockmanager'),
  

    # stock — list, edit, delete
    path('stock/', views.stock, name='stock'),
    path('stock/edit/<int:pk>/', views.stock_edit, name='stock_edit'),
    path('stock/delete/<int:pk>/', views.stock_delete, name='stock_delete'),
    path('sales/edit/<int:pk>/', views.sales_edit, name='sales_edit'),

    # sales — list, delete
    path('sales/', views.sales, name='sales'),
    path('sales/delete/<int:pk>/', views.sales_delete, name='sales_delete'),

    # supplier credit — list, edit, delete
    path('supplier_credit/', views.supplier_credit, name='supplier_credit'),
    path('supplier_credit/edit/<int:pk>/', views.supplier_edit, name='supplier_edit'),
    path('supplier_credit/delete/<int:pk>/', views.supplier_delete, name='supplier_delete'),

    # customer registration — list, edit, delete
    path('customer_registration/', views.customer_registration, name='customer_registration'),
    path('customer_registration/edit/<int:pk>/', views.customer_edit, name='customer_edit'),
    path('customer_registration/delete/<int:pk>/', views.customer_delete, name='customer_delete'),

    # customer deposit — list, edit, delete 
    path('customer_deposit/', views.customer_deposit, name='customer_deposit'),
    path('customer_deposit/edit/<int:pk>/', views.deposit_edit, name='deposit_edit'),
    path('customer_deposit/delete/<int:pk>/', views.deposit_delete, name='deposit_delete'),
    path('supplier_credit/pay/<int:supplier_id>/', views.supplier_pay, name='supplier_pay'),
    path('sales/receipt/<int:pk>/', views.sale_receipt, name='sale_receipt'),
    path('customer_deposit/pay/<int:deposit_id>/', views.pay_deposit, name='pay_deposit'),
]