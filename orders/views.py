from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from cart.cart import Cart
from .models import Order, OrderItem, OrderStatusUpdate, Coupon
from .access import get_order_or_403
from config.ratelimit import is_rate_limited, record_attempt
import json


def checkout_view(request):
    cart = Cart(request)
    if cart.is_empty():
        messages.warning(request, 'Your cart is empty.')
        return redirect('full_menu')

    addresses = []
    if request.user.is_authenticated:
        addresses = request.user.addresses.all()

    context = {
        'cart': cart,
        'addresses': addresses,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'orders/checkout.html', context)


def _resolve_coupon(coupon_code, subtotal):
    """Looks up and validates a coupon code against the cart subtotal.
    Returns (coupon_or_None, discount_amount) — never raises, since an
    invalid/expired/missing code should just mean "no discount", not
    a failed checkout."""
    if not coupon_code:
        return None, 0
    try:
        candidate = Coupon.objects.select_for_update().get(code=coupon_code)
    except Coupon.DoesNotExist:
        return None, 0
    valid, _reason = candidate.is_valid_for(subtotal)
    if not valid:
        return None, 0
    return candidate, candidate.calculate_discount(subtotal)


def place_order(request):
    if request.method != 'POST':
        return redirect('checkout')

    cart = Cart(request)
    if cart.is_empty():
        return redirect('cart')

    if is_rate_limited(request, 'place_order', max_attempts=20, window_seconds=3600):
        messages.error(request, 'Too many orders placed recently. Please try again later.')
        return redirect('checkout')
    record_attempt(request, 'place_order', window_seconds=3600)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except Exception:
        data = request.POST

    coupon_code = data.get('coupon_code', '').strip().upper()

    # Row-locked (inside _resolve_coupon's select_for_update) so two
    # simultaneous checkouts can't both pass the max_uses check before
    # either commits (a coupon capped at N uses could otherwise be
    # redeemed N+1+ times by concurrent requests). select_for_update()
    # is a no-op hint on SQLite but takes effect on Postgres/MySQL in
    # a real deployment, which is what this guards.
    with transaction.atomic():
        coupon, discount = _resolve_coupon(coupon_code, cart.get_subtotal())

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=data.get('full_name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            street_address=data.get('street_address', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            zip_code=data.get('zip_code', ''),
            country=data.get('country', 'United States'),
            subtotal=cart.get_subtotal(),
            tax=cart.get_tax(),
            delivery_fee=cart.get_delivery_fee(),
            discount=discount,
            total=cart.get_total() - discount,
            payment_method=data.get('payment_method', 'cash'),
            notes=data.get('notes', ''),
            coupon=coupon,
            estimated_delivery=timezone.now() + timedelta(minutes=30),
        )

        for cart_item in cart:
            OrderItem.objects.create(
                order=order,
                menu_item=cart_item.get('item'),
                name=cart_item['name'],
                price=cart_item['price'],
                quantity=cart_item['quantity'],
            )

        OrderStatusUpdate.objects.create(order=order, status=Order.STATUS_PENDING, note='Order placed successfully.')

        if coupon:
            coupon.times_used += 1
            coupon.save()

    cart.clear()
    request.session['last_order_id'] = order.id

    if order.payment_method == 'cash':
        order.payment_status = 'pending'
        order.save()
        return redirect('order_success', order_number=order.order_number)
    elif order.payment_method == 'stripe':
        return redirect('payment_stripe', order_id=order.id)
    return redirect('order_success', order_number=order.order_number)


def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not get_order_or_403(request, order):
        return HttpResponseForbidden("You do not have permission to view this order.")
    return render(request, 'orders/order_success.html', {'order': order})


def order_tracking(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not get_order_or_403(request, order):
        return HttpResponseForbidden("You do not have permission to view this order.")
    status_updates = order.status_updates.all()
    statuses = [
        Order.STATUS_PENDING,
        Order.STATUS_CONFIRMED,
        Order.STATUS_PREPARING,
        Order.STATUS_OUT_FOR_DELIVERY,
        Order.STATUS_DELIVERED,
    ]
    current_index = statuses.index(order.status) if order.status in statuses else 0
    return render(request, 'orders/tracking.html', {
        'order': order,
        'status_updates': status_updates,
        'statuses': statuses,
        'current_index': current_index,
    })


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/history.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/detail.html', {'order': order})


@login_required
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if request.method == 'POST' and order.can_cancel:
        order.status = Order.STATUS_CANCELLED
        order.save()
        OrderStatusUpdate.objects.create(order=order, status=Order.STATUS_CANCELLED, note='Cancelled by customer.')
        messages.success(request, 'Order cancelled successfully.')
    else:
        messages.error(request, 'This order cannot be cancelled.')
    return redirect('order_detail', order_number=order_number)


def apply_coupon(request):
    if request.method == 'POST':
        cart = Cart(request)
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip().upper()
        except Exception:
            code = request.POST.get('code', '').strip().upper()
        try:
            coupon = Coupon.objects.get(code=code)
            valid, reason = coupon.is_valid_for(cart.get_subtotal())
            if not valid:
                return JsonResponse({'status': 'error', 'message': reason})
            discount = coupon.calculate_discount(cart.get_subtotal())
            return JsonResponse({
                'status': 'ok',
                'code': coupon.code,
                'discount': str(discount),
                'message': f'Coupon applied! You save ${discount}',
            })
        except Coupon.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid or expired coupon code.'})
    return JsonResponse({'status': 'error'}, status=405)
