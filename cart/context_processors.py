from decimal import Decimal
from .cart import Cart, TAX_RATE

def cart_processor(request):
    cart = Cart(request)
    return {
        'cart': cart,
        'cart_count': cart.get_item_count(),
        'cart_total': cart.get_total(),
        # Available globally so "Tax (X%)" labels derive from the one
        # real constant instead of being hardcoded as "8%" text in
        # five separate templates (checkout, cart, the navbar cart
        # dropdown, plus order-history pages showing a *placed*
        # order's stored total, which correctly keep their own static
        # label since there's no historical tax_rate stored per order).
        'tax_rate_percent': (TAX_RATE * 100).quantize(Decimal('1')) if (TAX_RATE * 100) == (TAX_RATE * 100).to_integral_value() else (TAX_RATE * 100).normalize(),
    }
