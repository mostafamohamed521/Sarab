import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from rest_framework.authtoken.models import Token

from config.ratelimit import is_rate_limited, record_attempt
from .models import FAQ, BlogPost


def about_view(request):
    return render(request, 'cms_pages/about.html')


def contact_view(request):
    return render(request, 'cms_pages/contact.html')


def faq_view(request):
    faqs = FAQ.objects.filter(is_active=True)
    return render(request, 'cms_pages/faq.html', {'faqs': faqs, 'faq_defaults': FAQ_DEFAULTS})


def privacy_policy(request):
    return render(request, 'cms_pages/privacy_policy.html')


def terms_conditions(request):
    return render(request, 'cms_pages/terms.html')


def refund_policy(request):
    return render(request, 'cms_pages/refund_policy.html')


def blog_list(request):
    posts = BlogPost.objects.filter(is_published=True)
    return render(request, 'cms_pages/blog_list.html', {'posts': posts})


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    related = BlogPost.objects.filter(is_published=True).exclude(pk=post.pk)[:3]
    return render(request, 'cms_pages/blog_detail.html', {'post': post, 'related': related})


# ── Customer support chat (n8n AI agent) ──────────────────────────────────
logger = logging.getLogger(__name__)
MAX_CHAT_MESSAGE_LEN = 600


def _get_session_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _user_context(request):
    """Auth token + display name for logged-in users (empty dict for guests).

    The token lets the n8n agent call /api/v1/orders/ and
    /api/v1/reservations/ AS THIS USER (those endpoints already filter by
    request.user - see api/views.py) and answer questions about their own
    real orders/reservations. Guests get nothing, and the agent's system
    prompt tells it to ask them to log in for anything account-specific.
    """
    if not request.user.is_authenticated:
        return {}
    token, _ = Token.objects.get_or_create(user=request.user)
    return {
        'auth_token': token.key,
        'user_name': request.user.get_full_name() or request.user.get_username(),
    }


def _extract_reply(data):
    """n8n can answer {"reply": ...}, [{"reply": ...}] or the raw agent
    output {"output": ...}; accept all of them."""
    if isinstance(data, list):
        data = data[0] if data else {}
    if isinstance(data, dict):
        for key in ('reply', 'output', 'text', 'message'):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def support_page(request):
    session_id = _get_session_id(request)
    chat_config = {
        'mode': settings.SUPPORT_CHAT_MODE,
        'serverUrl': reverse('support_chat_api'),
        'sessionId': session_id,
        'maxLength': MAX_CHAT_MESSAGE_LEN,
    }
    if settings.SUPPORT_CHAT_MODE == 'browser':
        # Browser talks to n8n directly (free PythonAnywhere accounts can't
        # reach n8n.cloud from the server). Only the user's own token is sent.
        chat_config['webhookUrl'] = settings.N8N_WEBHOOK_URL
        chat_config['user'] = _user_context(request)
    return render(request, 'cms_pages/support.html', {'chat_config': chat_config})


@require_POST
def support_chat_api(request):
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    message = str(data.get('message', '')).strip() if isinstance(data, dict) else ''
    if not message:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)
    message = message[:MAX_CHAT_MESSAGE_LEN]

    # The LLM costs money per call - keep scripted abuse in check.
    if is_rate_limited(request, 'support_chat', max_attempts=30, window_seconds=300):
        return JsonResponse({'error': 'Too many messages - please wait a few minutes.'}, status=429)
    record_attempt(request, 'support_chat', window_seconds=300)

    payload = {'message': message, 'session_id': _get_session_id(request)}
    payload.update(_user_context(request))

    try:
        resp = requests.post(settings.N8N_WEBHOOK_URL, json=payload, timeout=settings.N8N_TIMEOUT)
        resp.raise_for_status()
        reply = _extract_reply(resp.json())
    except (requests.RequestException, ValueError):
        logger.exception('n8n support webhook call failed')
        return JsonResponse(
            {'error': 'There was a problem connecting to the support service. Please try again.'},
            status=502,
        )

    return JsonResponse({'reply': reply or 'Sorry, I have no response right now.'})


FAQ_DEFAULTS = [
    ('What are your delivery hours?', 'We deliver Wednesday through Sunday from 10 AM to 10:30 PM. Fridays and Saturdays until 11 PM.'),
    ('How long does delivery take?', 'Most deliveries arrive within 20–30 minutes depending on your distance from our kitchen. During peak hours (12–2 PM and 6–9 PM) allow up to 40 minutes.'),
    ('Do you offer vegan or vegetarian options?', 'Absolutely! We have a dedicated section for vegetarian and vegan diners. Look for the 🌿 leaf icon on vegetarian items and the V badge on vegan choices.'),
    ('Can I modify my order after placing it?', 'Orders can be modified within 5 minutes of placement by calling +1 (800) 123-4567. After preparation begins, changes are unfortunately not possible.'),
    ('What is your refund or cancellation policy?', 'Full refunds are available for cancellations within 5 minutes. For food quality issues, contact us within 30 minutes of delivery with a photo — we\'ll re-make or fully refund, no questions asked.'),
    ('Do you cater for large groups or events?', 'Yes! We love catering for events, corporate lunches, birthdays and more. Groups of 20+ receive a special catering menu. Email events@sarabfood.com to enquire.'),
    ('Is the food halal?', 'Yes — all our meat is certified halal. We do not serve pork or pork products.'),
    ('How do I track my order?', 'Once confirmed, you\'ll receive a tracking link via email. You can also track from the "My Orders" section in your account using your order number.'),
]