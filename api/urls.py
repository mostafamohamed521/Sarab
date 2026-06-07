from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'menu', views.MenuItemViewSet)
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'reservations', views.ReservationViewSet, basename='reservation')
router.register(r'reviews', views.ReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('rest_framework.urls')),
]
