from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=200)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)  # buying price
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # selling price
    quantity = models.IntegerField(default=0)  # current stock level

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # how much we owe them
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name


class StockArrival(models.Model):
    # recorded every time new stock comes in from a supplier
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_received = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)  # cost at time of arrival
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # selling price set at arrival
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity_received} units"


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # price at time of sale
    total_price = models.DecimalField(max_digits=10, decimal_places=2)  # quantity x unit_price
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # delivery distance
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 0 or 30,000 UGX
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # free delivery if order is 500k+ and within 10km, otherwise 30k charge
        if self.total_price >= 500000 and self.distance_km <= 10:
            self.transport_fee = 0
        else:
            self.transport_fee = 30000
        super().save(*args, **kwargs)

    def grand_total(self):
        # final amount customer pays
        return self.total_price + self.transport_fee

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class Customer(models.Model):
    # salary earners registered under the deposit scheme
    full_name = models.CharField(max_length=200)  # must match name on National ID
    NIN = models.CharField(max_length=20, unique=True)  # National Identification Number
    phone = models.CharField(max_length=20)
    employer = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)

    PRODUCT_CHOICES = [
        ('cement_cem2', 'Cement CEM II N'),
        ('cement_cem3', 'Cement CEM III N'),
        ('iron_bar_10', 'Iron Bar 10mm'),
        ('iron_bar_12', 'Iron Bar 12mm'),
        ('iron_bar_16', 'Iron Bar 16mm'),
        ('iron_sheet_26', 'Iron Sheets 26G'),
        ('iron_sheet_28', 'Iron Sheets 28G'),
        ('iron_sheet_30', 'Iron Sheets 30G'),
    ]
    preferred_product = models.CharField(max_length=50, choices=PRODUCT_CHOICES)
    registration_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.NIN})"


class CustomerDeposit(models.Model):
    # each row is one deposit payment by a scheme customer
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    amount_deposited = models.DecimalField(max_digits=10, decimal_places=2)  # amount paid today
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # price per unit at deposit time
    units_equivalent = models.IntegerField(default=0)  # units today's deposit can buy

    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('ready_pickup', 'Ready for Pickup'),
        ('collected', 'Collected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # auto-calculate how many units the deposit amount can buy
        if self.unit_price > 0:
            self.units_equivalent = int(self.amount_deposited / self.unit_price)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.full_name} - {self.amount_deposited} UGX"