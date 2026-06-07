from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from cart.cart import Cart
from .models import Order, OrderItem, OrderStatusUpdate, Coupon
from accounts.models import Address
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
        'stripe_key': 'pk_test_your_key_here',
    }
    return render(request, 'orders/checkout.html', context)


def place_order(request):
    if request.method != 'POST':
        return redirect('checkout')

    cart = Cart(request)
    if cart.is_empty():
        return redirect('cart')

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except Exception:
        data = request.POST

    # Coupon check
    coupon = None
    coupon_code = data.get('coupon_code', '').strip().upper()
    discount = 0
    if coupon_code:
        try:
            coupon = Coupon.objects.get(
                code=coupon_code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_until__gte=timezone.now(),
            )
            discount = coupon.calculate_discount(cart.get_subtotal())
        except Coupon.DoesNotExist:
            pass

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
    return render(request, 'orders/order_success.html', {'order': order})


def order_tracking(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
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
    orders = Order.objects.filter(user=request.user)
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
            coupon = Coupon.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_until__gte=timezone.now(),
            )
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
