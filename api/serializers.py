from rest_framework import serializers
from menu.models import Category, MenuItem, Tag
from orders.models import Order, OrderItem
from reservations.models import Reservation
from reviews.models import Review
from accounts.models import CustomUser


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


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'full_name', 'email', 'phone',
            'street_address', 'city', 'state', 'zip_code',
            'subtotal', 'tax', 'delivery_fee', 'discount', 'total',
            'payment_method', 'payment_status', 'status', 'status_display',
            'notes', 'estimated_delivery', 'created_at', 'items',
        ]

    def get_status_display(self, obj):
        return obj.get_status_display()


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            'id', 'confirmation_code', 'full_name', 'email', 'phone',
            'date', 'time', 'guests', 'occasion', 'special_requests', 'status',
        ]


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'menu_item', 'rating', 'title', 'comment', 'user_name', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email
