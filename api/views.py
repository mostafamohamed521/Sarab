from django.db.models import Avg, Count, Q
from rest_framework import viewsets, permissions, filters
from menu.models import Category, MenuItem
from orders.models import Order
from reservations.models import Reservation
from reviews.models import Review
from .serializers import (
    CategorySerializer, MenuItemSerializer, OrderSerializer,
    ReservationSerializer, ReviewSerializer,
)
from .permissions import IsOwnerOrReadOnly


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True).annotate(
        _item_count=Count('items', filter=Q(items__is_available=True), distinct=True)
    )
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class MenuItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MenuItem.objects.filter(is_available=True).select_related('category').prefetch_related('tags').annotate(
        _avg_rating=Avg('reviews__rating'), _review_count=Count('reviews', distinct=True)
    )
    serializer_class = MenuItemSerializer
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['price', 'name', 'created_at']
    ordering = ['order']

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__slug=category)
        featured = self.request.query_params.get('featured')
        if featured:
            qs = qs.filter(is_featured=True)
        return qs


class OrderViewSet(viewsets.ModelViewSet):
    """
    List/retrieve/create only. Orders are never edited after placement
    through this API (pricing, payment_status and status are read-only
    on the serializer, and there is no supported "edit my order" flow
    elsewhere in the app either) — cancellation is handled by the
    dedicated `cancel_order` web view, which enforces the same
    ownership + can_cancel business rule.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Reservation.objects.filter(user=self.request.user)
        return Reservation.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Anyone can read approved reviews. Only the review's own author may
    create/update/delete it — previously there was no object-level
    ownership check, so any authenticated user could edit or delete
    someone else's review by ID (IDOR).
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            # Owners can also see/manage their own not-yet-approved review.
            return Review.objects.filter(Q(is_approved=True) | Q(user=self.request.user))
        return Review.objects.filter(is_approved=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
