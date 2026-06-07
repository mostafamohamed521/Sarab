from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from orders.models import Order
import json

try:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False


def payment_stripe(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'payments/stripe_payment.html', {
        'order': order,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


@require_POST
def create_payment_intent(request):
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        if STRIPE_AVAILABLE:
            intent = stripe.PaymentIntent.create(
                amount=int(order.total * 100),
                currency='usd',
                metadata={'order_id': order_id, 'order_number': order.order_number},
            )
            order.stripe_payment_intent = intent.id
            order.save()
            return JsonResponse({'client_secret': intent.client_secret})
        else:
            return JsonResponse({'error': 'Stripe not configured'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        if STRIPE_AVAILABLE:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                order_id = payment_intent['metadata'].get('order_id')
                if order_id:
                    Order.objects.filter(id=order_id).update(payment_status='paid', status=Order.STATUS_CONFIRMED)
    except Exception as e:
        return HttpResponse(status=400)
    return HttpResponse(status=200)


def payment_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    order.payment_status = 'paid'
    order.status = Order.STATUS_CONFIRMED
    order.save()
    return render(request, 'payments/success.html', {'order': order})


def payment_failed(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'payments/failed.html', {'order': order})


def invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'payments/invoice.html', {'order': order})
