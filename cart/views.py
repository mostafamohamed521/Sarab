from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from menu.models import MenuItem
from .cart import Cart
import json

MAX_ITEM_QUANTITY = 50


def _parse_quantity(data, request):
    raw = data.get('quantity', request.POST.get('quantity', 1))
    try:
        quantity = int(raw)
    except (TypeError, ValueError):
        return None
    if quantity > MAX_ITEM_QUANTITY:
        quantity = MAX_ITEM_QUANTITY
    return quantity


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/cart.html', {'cart': cart})


@require_POST
def cart_add(request, item_id):
    cart = Cart(request)
    item = get_object_or_404(MenuItem, id=item_id, is_available=True)
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else {}
    except Exception:
        data = {}
    quantity = _parse_quantity(data, request)
    if quantity is None:
        return JsonResponse({'status': 'error', 'message': 'Quantity must be a number.'}, status=400)
    cart.add(item, quantity=quantity)
    return JsonResponse({
        'status': 'ok',
        'cart_count': cart.get_item_count(),
        'cart_total': str(cart.get_total()),
        'message': f'{item.name} added to cart!',
    })


@require_POST
def cart_remove(request, item_id):
    cart = Cart(request)
    cart.remove_by_id(item_id)
    return JsonResponse({
        'status': 'ok',
        'cart_count': cart.get_item_count(),
        'cart_total': str(cart.get_total()),
    })


@require_POST
def cart_update(request, item_id):
    cart = Cart(request)
    item = get_object_or_404(MenuItem, id=item_id)
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else {}
    except Exception:
        data = {}
    quantity = _parse_quantity(data, request)
    if quantity is None:
        return JsonResponse({'status': 'error', 'message': 'Quantity must be a number.'}, status=400)
    if quantity <= 0:
        cart.remove_by_id(item_id)
    else:
        cart.add(item, quantity=quantity, override_quantity=True)
    return JsonResponse({
        'status': 'ok',
        'cart_count': cart.get_item_count(),
        'cart_total': str(cart.get_total()),
        'subtotal': str(cart.get_subtotal()),
    })


def cart_summary(request):
    cart = Cart(request)
    return JsonResponse({
        'count': cart.get_item_count(),
        'subtotal': str(cart.get_subtotal()),
        'tax': str(cart.get_tax()),
        'delivery': str(cart.get_delivery_fee()),
        'total': str(cart.get_total()),
    })
