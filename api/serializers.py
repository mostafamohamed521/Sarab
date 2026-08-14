from decimal import Decimal
from datetime import date
from rest_framework import serializers
from menu.models import Category, MenuItem, Tag
from orders.models import Order, OrderItem
from reservations.models import Reservation
from reviews.models import Review
from cart.cart import TAX_RATE, DELIVERY_FEE, FREE_DELIVERY_THRESHOLD


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.ReadOnlyField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'item_count']


class MenuItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    tags = TagSerializer(many=True, read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    discount_percent = serializers.ReadOnlyField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'slug', 'description', 'short_description',
            'category', 'category_id', 'price', 'old_price', 'badge',
            'calories', 'prep_time', 'is_available', 'is_vegetarian',
            'is_vegan', 'is_gluten_free', 'is_spicy', 'is_featured',
            'tags', 'average_rating', 'review_count', 'discount_percent', 'image_url',
        ]

    def get_image_url(self, obj):
        return obj.get_image_url()


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ['id', 'name', 'price', 'quantity', 'subtotal']


class OrderItemInputSerializer(serializers.Serializer):
    """Used only to accept `{menu_item, quantity}` pairs on order creation.
    Price is always looked up server-side from the current MenuItem —
    never trusted from the client."""
    menu_item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.filter(is_available=True))
    quantity = serializers.IntegerField(min_value=1, max_value=50)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.SerializerMethodField()
    # Accepted only on create; ignored/read-only afterwards (see below).
    order_items = OrderItemInputSerializer(many=True, write_only=True, required=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'full_name', 'email', 'phone',
            'street_address', 'city', 'state', 'zip_code', 'country',
            'subtotal', 'tax', 'delivery_fee', 'discount', 'total',
            'payment_method', 'payment_status', 'status', 'status_display',
            'notes', 'estimated_delivery', 'created_at', 'items', 'order_items',
        ]
        # Pricing and status are always server-computed / staff-managed —
        # never accepted from the client. Without this, any authenticated
        # user could POST/PATCH their own order's total, discount or
        # payment_status directly (mass assignment / price tampering).
        read_only_fields = [
            'id', 'order_number', 'subtotal', 'tax', 'delivery_fee', 'discount',
            'total', 'payment_status', 'status', 'estimated_delivery', 'created_at',
        ]

    def get_status_display(self, obj):
        return obj.get_status_display()

    def create(self, validated_data):
        items_data = validated_data.pop('order_items')
        request = self.context['request']

        subtotal = Decimal('0.00')
        prepared_items = []
        for entry in items_data:
            menu_item = entry['menu_item']
            quantity = entry['quantity']
            line_total = menu_item.price * quantity
            subtotal += line_total
            prepared_items.append((menu_item, quantity))

        tax = (subtotal * TAX_RATE).quantize(Decimal('0.01'))
        delivery_fee = Decimal('0.00') if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_FEE
        total = subtotal + tax + delivery_fee

        order = Order.objects.create(
            user=request.user,
            subtotal=subtotal,
            tax=tax,
            delivery_fee=delivery_fee,
            discount=Decimal('0.00'),
            total=total,
            **validated_data,
        )
        for menu_item, quantity in prepared_items:
            OrderItem.objects.create(
                order=order, menu_item=menu_item, name=menu_item.name,
                price=menu_item.price, quantity=quantity,
            )
        return order


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            'id', 'confirmation_code', 'full_name', 'email', 'phone',
            'date', 'time', 'guests', 'occasion', 'special_requests', 'status',
        ]
        # confirmation_code is server-generated; status is staff-managed
        # (customers cancel through the dedicated cancel action/view,
        # which also enforces business rules) — without this a customer
        # could PATCH their own reservation straight to 'confirmed' or
        # 'completed'.
        read_only_fields = ['id', 'confirmation_code', 'status']

    def validate_date(self, value):
        # Mirrors ReservationForm.clean_date — the web form's HTML
        # `min` attribute is client-side only, and this API had no
        # equivalent check at all.
        if value < date.today():
            raise serializers.ValidationError('Reservation date cannot be in the past.')
        return value

    def validate_guests(self, value):
        if value < 1 or value > 20:
            raise serializers.ValidationError('Guests must be between 1 and 20.')
        return value


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'menu_item', 'rating', 'title', 'comment', 'user_name', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email
