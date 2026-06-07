from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_detail, name='cart'),
    path('add/<int:item_id>/', views.cart_add, name='cart_add'),
    path('remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('summary/', views.cart_summary, name='cart_summary'),
]
