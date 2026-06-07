from django.urls import path
from . import views

urlpatterns = [
    path('stripe/<int:order_id>/', views.payment_stripe, name='payment_stripe'),
    path('create-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('success/<str:order_number>/', views.payment_success, name='payment_success'),
    path('failed/<str:order_number>/', views.payment_failed, name='payment_failed'),
    path('invoice/<str:order_number>/', views.invoice, name='invoice'),
]
