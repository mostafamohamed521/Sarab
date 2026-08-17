from django.contrib import admin
from .models import Reservation, Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'capacity', 'location', 'is_active']
    list_editable = ['is_active']


def _make_reservation_status_action(status_value, status_label):
    # Reservations have no separate status-history model (unlike
    # orders' OrderStatusUpdate), so a plain bulk update is safe here.
    def action(modeladmin, request, queryset):
        updated = queryset.exclude(status=status_value).update(status=status_value)
        modeladmin.message_user(request, f'{updated} reservation(s) marked as {status_label}.')
    action.__name__ = f'mark_{status_value}'
    action.short_description = f'Mark selected as {status_label}'
    # See the identical note in orders/admin.py — custom actions don't
    # require 'change' permission unless declared explicitly.
    action.allowed_permissions = ('change',)
    return action


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['confirmation_code', 'full_name', 'date', 'time', 'guests', 'status']
    list_filter = ['status', 'date']
    search_fields = ['full_name', 'email', 'confirmation_code']
    list_editable = ['status']
    actions = [
        _make_reservation_status_action(Reservation.STATUS_CONFIRMED, 'Confirmed'),
        _make_reservation_status_action(Reservation.STATUS_COMPLETED, 'Completed'),
        _make_reservation_status_action(Reservation.STATUS_NO_SHOW, 'No Show'),
        _make_reservation_status_action(Reservation.STATUS_CANCELLED, 'Cancelled'),
    ]
