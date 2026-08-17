"""
Site-wide Django Admin dashboard customization.

Deliberately lives here (config/) rather than inside any single app's
admin.py — it customizes the shared admin.site object itself (the
dashboard access gate and the index page), not any one app's models,
so it doesn't belong to accounts, orders, or any other app in
particular. Imported once, for its side effects, from
accounts/admin.py (Django's admin autodiscovery only auto-imports
each app's own admin.py, not arbitrary modules like this one).
"""
import logging
from django.contrib import admin
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger('security')


def _admin_dashboard_only(request):
    """
    Django's own admin gate only checks is_staff — any staff account
    could log into /admin/ and see whatever models their assigned
    permissions allow, regardless of this project's own customer/
    staff/admin role distinction. This ties actual dashboard access to
    that role (reusing CustomUser.is_admin_user, already defined on
    the model but never wired to anything real) so only role=admin
    (or a superuser, who always gets in as a safety net) can reach the
    dashboard at all — a staff-role account is blocked even if it
    somehow also had is_staff=True.
    """
    user = request.user
    allowed = bool(
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and getattr(user, 'is_admin_user', False)
    )
    if user.is_authenticated and user.is_staff and not allowed:
        # is_staff=True but blocked by the stricter role check above —
        # worth a record, since this is exactly the "staff account
        # trying to reach admin" scenario this gate exists to catch.
        logger.warning('Admin dashboard access denied for staff user %s (role=%s)', user.email, user.role)
    return allowed


def _build_dashboard_stats():
    """
    At-a-glance numbers for the admin index page — the dashboard used
    to be nothing but the bare app/model list Django Admin shows by
    default, with no overview of what actually needs attention.
    Imports are local to avoid any import-order issues with Django's
    admin autodiscovery (this module loads very early).
    """
    from orders.models import Order
    from reservations.models import Reservation
    from menu.models import MenuItem, ContactMessage
    from reviews.models import Review

    today = timezone.localdate()
    today_orders = Order.objects.filter(created_at__date=today)
    revenue_today = today_orders.filter(payment_status='paid').aggregate(total=Sum('total'))['total'] or 0

    return {
        'dashboard_stats': [
            {'label': "Today's Orders", 'value': today_orders.count(),
             'url': '/admin/orders/order/?created_at__gte=' + str(today)},
            {'label': "Today's Revenue", 'value': f'${revenue_today:.2f}', 'url': None},
            {'label': 'Pending Orders', 'value': Order.objects.filter(status=Order.STATUS_PENDING).count(),
             'url': '/admin/orders/order/?status__exact=' + Order.STATUS_PENDING},
            {'label': 'Pending Reservations',
             'value': Reservation.objects.filter(status=Reservation.STATUS_PENDING).count(),
             'url': '/admin/reservations/reservation/?status__exact=' + Reservation.STATUS_PENDING},
            {'label': 'Unread Messages', 'value': ContactMessage.objects.filter(is_read=False).count(),
             'url': '/admin/menu/contactmessage/?is_read__exact=0'},
            {'label': 'Reviews Awaiting Approval',
             'value': Review.objects.filter(is_approved=False).count(),
             'url': '/admin/reviews/review/?is_approved__exact=0'},
            {'label': 'Unavailable Menu Items',
             'value': MenuItem.objects.filter(is_available=False).count(),
             'url': '/admin/menu/menuitem/?is_available__exact=0'},
        ],
        'recent_orders': Order.objects.order_by('-created_at')[:5],
    }


def _dashboard_index(request, extra_context=None):
    # Captured once at module load, before the line below replaces
    # admin.site.index — calling the class method explicitly with
    # admin.site as self avoids recursing into this same function.
    extra_context = extra_context or {}
    extra_context.update(_build_dashboard_stats())
    return _original_admin_index(admin.site, request, extra_context)


_original_admin_index = admin.site.__class__.index
admin.site.has_permission = _admin_dashboard_only
admin.site.index = _dashboard_index
