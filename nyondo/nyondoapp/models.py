from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError


# --- Reusable validators ---

# Ugandan phone: accepts 07XXXXXXXX, 256XXXXXXXXX, or +256XXXXXXXXX
ugandan_phone_validator = RegexValidator(
    regex=r'^(\+256|256|0)7\d{8}$',
    message='Enter a valid Ugandan phone number e.g. 0712345678 or 256712345678'
)

# Uganda NIN format: letters + 14 digits e.g. CM20100012345678
nin_validator = RegexValidator(
    regex=r'^[A-Z]{2}\d{14}$',
    message='Enter a valid NIN e.g. CM20100012345678 (2 letters + 14 digits)'
)


class Product(models.Model):
    name = models.CharField(max_length=200)

    # unit_cost must be at least 1 UGX — zero/negative buying price makes no sense
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1, message='Unit cost must be at least 1 UGX')]
    )

    # unit_price must also be at least 1 UGX
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1, message='Unit price must be at least 1 UGX')]
    )

    # quantity can be 0 (out of stock) but never negative
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0, message='Stock quantity cannot be negative')]
    )

    def clean(self):
        # unit_price should never be less than unit_cost — selling at a loss is a data error
        if self.unit_price and self.unit_cost:
            if self.unit_price < self.unit_cost:
                raise ValidationError({
                    'unit_price': 'Selling price cannot be less than the buying price (unit cost).'
                })

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200)

    # enforce valid Ugandan phone format
    phone = models.CharField(
        max_length=20,
        validators=[ugandan_phone_validator]
    )

    address = models.CharField(max_length=255, blank=True)

    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    # quantity supplied must be 0 or more — negative makes no sense
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0, message='Quantity cannot be negative')]
    )

    # credit_amount is what we owe this supplier — must be 0 or more
    credit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0, message='Credit amount cannot be negative')]
    )

    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name


class StockArrival(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)

    # must receive at least 1 unit — recording 0 or negative arrival is meaningless
    quantity_received = models.IntegerField(
        validators=[MinValueValidator(1, message='Quantity received must be at least 1')]
    )

    # cost at the time stock arrived — must be positive
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1, message='Unit cost must be at least 1 UGX')]
    )

    # selling price set when stock arrived — must be positive
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1, message='Unit price must be at least 1 UGX')]
    )

    date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # selling price on arrival must not be below the cost paid for the stock
        if self.unit_price and self.unit_cost:
            if self.unit_price < self.unit_cost:
                raise ValidationError({
                    'unit_price': 'Selling price cannot be less than unit cost for this stock arrival.'
                })

    def __str__(self):
        return f"{self.product.name} - {self.quantity_received} units"


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # must sell at least 1 unit
    quantity = models.IntegerField(
        validators=[MinValueValidator(1, message='Sale quantity must be at least 1')]
    )

    # price per unit at time of sale — must be positive
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1, message='Unit price must be at least 1 UGX')]
    )

    # total before transport — must be positive (quantity x unit_price)
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1, message='Total price must be at least 1 UGX')]
    )

    # delivery distance in km — 0 means pickup (no delivery), cannot be negative
    distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0, message='Distance cannot be negative')]
    )

    # auto-set in save() — no validator needed here since we control it
    transport_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # total_price must match quantity x unit_price — catches form tampering or data entry errors
        if self.quantity and self.unit_price and self.total_price:
            expected = self.quantity * self.unit_price
            if abs(float(self.total_price) - float(expected)) > 0.01:  # allow tiny float rounding
                raise ValidationError({
                    'total_price': f'Total price must equal quantity × unit price ({expected} UGX).'
                })

        # check enough stock exists before allowing the sale
        if self.product_id and self.quantity:
            try:
                product = Product.objects.get(pk=self.product_id)
                if self.quantity > product.quantity:
                    raise ValidationError({
                        'quantity': f'Not enough stock. Only {product.quantity} units available.'
                    })
            except Product.DoesNotExist:
                pass  # ForeignKey constraint will handle this

    def save(self, *args, **kwargs):
        total = float(self.total_price)
        distance = float(self.distance_km) if self.distance_km else 0

        # free delivery: order >= 500,000 UGX AND within 10 km; otherwise 30,000 UGX surcharge
        if total >= 500000 and distance <= 10:
            self.transport_fee = 0
        else:
            self.transport_fee = 30000

        super().save(*args, **kwargs)

    def grand_total(self):
        # what the customer actually pays: product total + transport fee
        return self.total_price + self.transport_fee

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class Customer(models.Model):
    # full name must match what appears on their National ID
    full_name = models.CharField(max_length=200)

    # NIN must be unique and follow the Ugandan format
    NIN = models.CharField(
        max_length=20,
        unique=True,
        validators=[nin_validator]
    )

    # must be a valid Ugandan phone number
    phone = models.CharField(
        max_length=20,
        validators=[ugandan_phone_validator]
    )

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

    # constrained to the choices list above — Django enforces this at form level
    preferred_product = models.CharField(max_length=50, choices=PRODUCT_CHOICES)

    registration_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.NIN})"


class CustomerDeposit(models.Model):

    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('ready_pickup', 'Ready for Pickup'),
        ('collected', 'Collected'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)

    # deposit must be a real positive amount — zero deposits are meaningless
    amount_deposited = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1, message='Deposit amount must be at least 1 UGX')]
    )

    # price per unit at the time of this deposit — used to compute units_equivalent
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1, message='Unit price must be at least 1 UGX')]
    )

    # how many units the customer is requesting/reserving
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0, message='Quantity cannot be negative')]
    )

    # auto-calculated in save(): int(amount_deposited / unit_price)
    units_equivalent = models.IntegerField(default=0)

    # extra amount paid at the time of pickup (if deposit didn't cover the full cost)
    amount_paid_on_pickup = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0, message='Amount paid on pickup cannot be negative')]
    )

    # constrained to PAYMENT_CHOICES — Django enforces at form level
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')

    # constrained to STATUS_CHOICES — Django enforces at form level
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    date = models.DateField(auto_now_add=True)

    def clean(self):
        # deposit cannot exceed what would be needed for 9999 units — sanity ceiling
        if self.amount_deposited and self.unit_price:
            if float(self.unit_price) > 0:
                max_reasonable_units = 9999
                max_amount = float(self.unit_price) * max_reasonable_units
                if float(self.amount_deposited) > max_amount:
                    raise ValidationError({
                        'amount_deposited': 'Deposit amount seems unreasonably large. Please double-check.'
                    })

        # status can only move forward: active → ready_pickup → collected
        # (only enforced on updates — skip for new records)
        if self.pk:
            try:
                old = CustomerDeposit.objects.get(pk=self.pk)
                status_order = ['active', 'ready_pickup', 'collected']
                old_index = status_order.index(old.status)
                new_index = status_order.index(self.status)
                if new_index < old_index:
                    raise ValidationError({
                        'status': f'Cannot revert status from "{old.status}" back to "{self.status}".'
                    })
            except CustomerDeposit.DoesNotExist:
                pass  # new record, skip the check

    def save(self, *args, **kwargs):
        amount = float(self.amount_deposited) if self.amount_deposited else 0
        price  = float(self.unit_price) if self.unit_price else 0

        # auto-calculate how many full units the deposit covers
        if price > 0:
            self.units_equivalent = int(amount / price)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.full_name} - {self.amount_deposited} UGX"