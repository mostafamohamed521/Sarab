from django.db import models
from django.conf import settings
import uuid


class Table(models.Model):
    number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField(default=4)
    location = models.CharField(max_length=50, choices=[('indoor', 'Indoor'), ('outdoor', 'Outdoor'), ('vip', 'VIP'), ('bar', 'Bar Area')], default='indoor')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"Table {self.number} (seats {self.capacity})"


class Reservation(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_NO_SHOW = 'no_show'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_NO_SHOW, 'No Show'),
    ]

    OCCASION_CHOICES = [
        ('', 'None'),
        ('birthday', 'Birthday'),
        ('anniversary', 'Anniversary'),
        ('business', 'Business Meeting'),
        ('date', 'Date Night'),
        ('family', 'Family Gathering'),
        ('other', 'Other'),
    ]

    confirmation_code = models.CharField(max_length=12, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True)
    # Guest info
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    # Reservation details
    date = models.DateField()
    time = models.TimeField()
    guests = models.PositiveIntegerField(default=2)
    occasion = models.CharField(max_length=20, choices=OCCASION_CHOICES, blank=True)
    special_requests = models.TextField(blank=True)
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.full_name} - {self.date} at {self.time}"

    def save(self, *args, **kwargs):
        if not self.confirmation_code:
            self.confirmation_code = 'RES' + uuid.uuid4().hex[:6].upper()
        super().save(*args, **kwargs)
