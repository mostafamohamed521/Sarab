import json
import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
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


N8N_WEBHOOK_URL = "https://sarab-support.app.n8n.cloud/webhook/sarab-support"


def support_page(request):
    if not request.session.session_key:
        request.session.create()
    return render(request, "cms_pages/support.html")


@require_POST
def support_chat_api(request):
    data = json.loads(request.body)
    message = data.get("message", "").strip()

    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key

    if not message:
        return JsonResponse({"error": "Message cannot be empty"}, status=400)

    try:
        resp = requests.post(
            N8N_WEBHOOK_URL,
            json={"message": message, "session_id": session_id},
            timeout=20,
        )
        resp.raise_for_status()
        reply = resp.json().get("reply", "Sorry, no response right now.")
    except requests.RequestException:
        reply = "There was a problem connecting to the support service. Please try again."

    return JsonResponse({"reply": reply})


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