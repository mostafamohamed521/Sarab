from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from menu.models import MenuItem
from .cart import Cart
import json


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
    quantity = int(data.get('quantity', request.POST.get('quantity', 1)))
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
    quantity = int(data.get('quantity', request.POST.get('quantity', 1)))
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
