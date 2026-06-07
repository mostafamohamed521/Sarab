from decimal import Decimal
from django.conf import settings
from menu.models import MenuItem

CART_SESSION_ID = getattr(settings, 'CART_SESSION_ID', 'cart')
TAX_RATE = Decimal('0.08')
DELIVERY_FEE = Decimal('3.99')
FREE_DELIVERY_THRESHOLD = Decimal('30.00')


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, item, quantity=1, override_quantity=False):
        item_id = str(item.id)
        if item_id not in self.cart:
            self.cart[item_id] = {
                'quantity': 0,
                'price': str(item.price),
                'name': item.name,
                'category': item.category.name,
                'image': item.get_image_url(),
            }
        if override_quantity:
            self.cart[item_id]['quantity'] = quantity
        else:
            self.cart[item_id]['quantity'] += quantity
        if self.cart[item_id]['quantity'] <= 0:
            self.remove(item)
        else:
            self.save()

    def remove(self, item):
        item_id = str(item.id)
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()

    def remove_by_id(self, item_id):
        item_id = str(item_id)
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()

    def save(self):
        self.session.modified = True

    def clear(self):
        del self.session[CART_SESSION_ID]
        self.session.modified = True

    def __iter__(self):
        item_ids = self.cart.keys()
        items_qs = MenuItem.objects.filter(id__in=item_ids)
        cart = self.cart.copy()
        for item in items_qs:
            cart[str(item.id)]['item'] = item
        for item_data in cart.values():
            item_data['price'] = Decimal(item_data['price'])
            item_data['total_price'] = item_data['price'] * item_data['quantity']
            yield item_data

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_subtotal(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def get_tax(self):
        return (self.get_subtotal() * TAX_RATE).quantize(Decimal('0.01'))

    def get_delivery_fee(self):
        if self.get_subtotal() >= FREE_DELIVERY_THRESHOLD:
            return Decimal('0.00')
        return DELIVERY_FEE

    def get_total(self):
        return self.get_subtotal() + self.get_tax() + self.get_delivery_fee()

    def get_item_count(self):
        return len(self)

    def is_empty(self):
        return len(self.cart) == 0
