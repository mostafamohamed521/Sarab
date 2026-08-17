from django.contrib import admin
from .models import Order, OrderItem, OrderStatusUpdate, Coupon


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']


class StatusUpdateInline(admin.TabularInline):
    model = OrderStatusUpdate
    extra = 0


def _make_status_action(status_value, status_label, note):
    """
    Builds one admin action per status. Goes through the same
    save() + OrderStatusUpdate.objects.create() pair the customer-
    facing cancel_order view already uses (rather than a bare
    queryset.update(), which would silently skip creating the status-
    history entry the customer-facing order-tracking page depends on).
    """
    def action(modeladmin, request, queryset):
        count = 0
        for order in queryset:
            if order.status == status_value:
                continue
            order.status = status_value
            order.save()
            OrderStatusUpdate.objects.create(order=order, status=status_value, note=note)
            count += 1
        modeladmin.message_user(request, f'{count} order(s) marked as {status_label}.')
    action.__name__ = f'mark_{status_value}'
    action.short_description = f'Mark selected as {status_label}'
    # Without this, Django lets anyone who can merely VIEW the Order
    # changelist (view_order permission) trigger a state-changing
    # action — custom actions don't require 'change' permission
    # automatically the way the built-in delete_selected requires
    # 'delete'. Explicit here rather than assumed.
    action.allowed_permissions = ('change',)
    return action


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'total', 'status', 'payment_method', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_status']
    search_fields = ['order_number', 'full_name', 'email', 'phone']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline, StatusUpdateInline]
    actions = [
        _make_status_action(Order.STATUS_CONFIRMED, 'Confirmed', 'Confirmed by staff.'),
        _make_status_action(Order.STATUS_PREPARING, 'Preparing', 'Preparation started.'),
        _make_status_action(Order.STATUS_READY, 'Ready', 'Ready for pickup/delivery.'),
        _make_status_action(Order.STATUS_OUT_FOR_DELIVERY, 'Out for Delivery', 'Out for delivery.'),
        _make_status_action(Order.STATUS_DELIVERED, 'Delivered', 'Delivered.'),
        _make_status_action(Order.STATUS_CANCELLED, 'Cancelled', 'Cancelled by staff.'),
        'mark_paid',
    ]

    def mark_paid(self, request, queryset):
        # Separate from the status actions above since payment_status
        # and status are two different fields — this is specifically
        # for cash orders collected in person.
        updated = queryset.exclude(payment_status='paid').update(payment_status='paid')
        self.message_user(request, f'{updated} order(s) marked as paid.')
    mark_paid.short_description = 'Mark selected as Paid (cash collected)'
    mark_paid.allowed_permissions = ('change',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'times_used', 'is_active', 'valid_until']
    list_editable = ['is_active']
