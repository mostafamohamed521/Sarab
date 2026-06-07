from django.urls import path
from . import views

urlpatterns = [
    path('', views.make_reservation, name='make_reservation'),
    path('confirmation/<str:code>/', views.reservation_confirmation, name='reservation_confirmation'),
    path('history/', views.reservation_history, name='reservation_history'),
    path('<str:code>/cancel/', views.cancel_reservation, name='cancel_reservation'),
]
