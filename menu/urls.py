from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/', views.full_menu, name='full_menu'),
    path('menu/<slug:slug>/', views.menu_item_detail, name='menu_item_detail'),
    path('menu-search/', views.menu_search, name='menu_search'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),
]
