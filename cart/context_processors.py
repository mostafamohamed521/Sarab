from .cart import Cart

def cart_processor(request):
    cart = Cart(request)
    return {
        'cart': cart,
        'cart_count': cart.get_item_count(),
        'cart_total': cart.get_total(),
    }
