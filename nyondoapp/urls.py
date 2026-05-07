from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/salesperson/', views.dashboard_salesperson, name='dashboard_salesperson'),
    path('dashboard/stockmanager/', views.dashboard_stockmanager, name='dashboard_stockmanager'),
    path('stock/', views.stock, name='stock'),
    path('sales/', views.sales, name='sales'),
    path('supplier_credit/', views.supplier_credit, name='supplier_credit'),
    path('customer_registration/', views.customer_registration, name='customer_registration'),
    path('customer_deposit/', views.customer_deposit, name='customer_deposit'),
]