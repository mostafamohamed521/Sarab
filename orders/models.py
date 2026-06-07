from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('fixed', 'Fixed Amount')], default='percent')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    def calculate_discount(self, amount):
        if self.discount_type == 'percent':
            return (amount * self.discount_value / 100).quantize(Decimal('0.01'))
        return min(self.discount_value, amount)


class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_PREPARING = 'preparing'
    STATUS_READY = 'ready'
    STATUS_OUT_FOR_DELIVERY = 'out_for_delivery'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_PREPARING, 'Preparing'),
        (STATUS_READY, 'Ready'),
        (STATUS_OUT_FOR_DELIVERY, 'Out for Delivery'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    PAYMENT_CASH = 'cash'
    PAYMENT_STRIPE = 'stripe'
    PAYMENT_PAYPAL = 'paypal'
    PAYMENT_WALLET = 'wallet'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Cash on Delivery'),
        (PAYMENT_STRIPE, 'Credit/Debit Card'),
        (PAYMENT_PAYPAL, 'PayPal'),
        (PAYMENT_WALLET, 'Wallet'),
    ]

    order_number = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    # Delivery info
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    # Payment
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    payment_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='pending')
    stripe_payment_intent = models.CharField(max_length=200, blank=True)
    # Status & tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        return 'SR' + uuid.uuid4().hex[:8].upper()

    def get_status_display_class(self):
        classes = {
            self.STATUS_PENDING: 'warning',
            self.STATUS_CONFIRMED: 'info',
            self.STATUS_PREPARING: 'primary',
            self.STATUS_READY: 'success',
            self.STATUS_OUT_FOR_DELIVERY: 'primary',
            self.STATUS_DELIVERED: 'success',
            self.STATUS_CANCELLED: 'danger',
            self.STATUS_REFUNDED: 'secondary',
        }
        return classes.get(self.status, 'secondary')

    @property
    def can_cancel(self):
        return self.status in [self.STATUS_PENDING, self.STATUS_CONFIRMED]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.name}"

    @property
    def subtotal(self):
        return self.price * self.quantity


class OrderStatusUpdate(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_updates')
    status = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.order.order_number} -> {self.status}"
