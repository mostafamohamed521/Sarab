from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('place/', views.place_order, name='place_order'),
    path('success/<str:order_number>/', views.order_success, name='order_success'),
    path('tracking/<str:order_number>/', views.order_tracking, name='order_tracking'),
    path('history/', views.order_history, name='order_history'),
    path('<str:order_number>/', views.order_detail, name='order_detail'),
    path('<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
]
