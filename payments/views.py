from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from orders.models import Order
from orders.access import get_order_or_403
import json

try:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False


def payment_stripe(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not get_order_or_403(request, order):
        return HttpResponseForbidden("You do not have permission to view this order.")
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
        if not get_order_or_403(request, order):
            return JsonResponse({'error': 'Not authorized for this order.'}, status=403)
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
    except Exception:
        return JsonResponse({'error': 'Unable to create payment intent.'}, status=400)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Authoritative source of truth for marking an order as paid.
    Stripe signs this request, so (unlike the browser redirect in
    payment_success) we can trust it without an ownership check.
    """
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
    except Exception:
        return HttpResponse(status=400)
    return HttpResponse(status=200)


def payment_success(request, order_number):
    """
    Landing page after the customer returns from Stripe's checkout.
    This is a browser redirect, NOT a trusted payment confirmation —
    it can be visited by anyone who guesses/knows the URL, and Stripe
    does not sign it. The only source of truth for "did the payment
    actually succeed" is the signed stripe_webhook above (or, for cash
    orders, staff marking the order paid in Django admin).

    Here we only ever verify against Stripe (when a payment intent is
    on file) and never trust the browser to declare success on its own.
    """
    order = get_object_or_404(Order, order_number=order_number)
    if not get_order_or_403(request, order):
        return HttpResponseForbidden("You do not have permission to view this order.")

    if order.payment_status != 'paid' and STRIPE_AVAILABLE and order.stripe_payment_intent:
        try:
            intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent)
            if intent.status == 'succeeded':
                order.payment_status = 'paid'
                order.status = Order.STATUS_CONFIRMED
                order.save()
        except Exception:
            # Can't verify right now; leave status untouched and let the
            # webhook (or staff) update it once it can be confirmed.
            pass

    return render(request, 'payments/success.html', {'order': order})


def payment_failed(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not get_order_or_403(request, order):
        return HttpResponseForbidden("You do not have permission to view this order.")
    return render(request, 'payments/failed.html', {'order': order})


def invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not get_order_or_403(request, order):
        return HttpResponseForbidden("You do not have permission to view this order.")
    return render(request, 'payments/invoice.html', {'order': order})
