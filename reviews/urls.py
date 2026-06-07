from django.urls import path
from . import views

urlpatterns = [
    path('review/<int:item_id>/', views.add_review, name='add_review'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:item_id>/', views.toggle_wishlist, name='toggle_wishlist'),
]
