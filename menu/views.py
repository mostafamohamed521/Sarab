from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Avg, Count
from .models import Category, MenuItem, ContactMessage
from config.ratelimit import is_rate_limited, record_attempt
import json


def home(request):
    categories = Category.objects.filter(is_active=True).annotate(
        _item_count=Count('items', filter=Q(items__is_available=True), distinct=True)
    )
    featured_items = _with_rating_annotations(
        MenuItem.objects.filter(is_available=True, is_featured=True)
    )[:6]
    menu_items = _with_rating_annotations(
        MenuItem.objects.filter(is_available=True).select_related('category')
    )[:12]
    return render(request, 'menu/home.html', {
        'categories': categories,
        'menu_items': menu_items,
        'featured_items': featured_items,
    })


def _with_rating_annotations(queryset):
    """Precompute average_rating/review_count for a list of items in one
    query instead of two extra queries per item (see MenuItem properties
    in menu/models.py)."""
    return queryset.annotate(
        _avg_rating=Avg('reviews__rating'), _review_count=Count('reviews', distinct=True)
    ).prefetch_related('tags')


def full_menu(request):
    categories = Category.objects.filter(is_active=True).annotate(
        _item_count=Count('items', filter=Q(items__is_available=True), distinct=True)
    )
    category_slug = request.GET.get('category', 'all')
    search_query = request.GET.get('q', '').strip()
    items = _with_rating_annotations(
        MenuItem.objects.filter(is_available=True).select_related('category')
    )

    if category_slug and category_slug != 'all':
        items = items.filter(category__slug=category_slug)
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    return render(request, 'menu/menu.html', {
        'categories': categories,
        'items': items,
        'active_category': category_slug,
        'search_query': search_query,
    })


def menu_item_detail(request, slug):
    item = get_object_or_404(MenuItem, slug=slug, is_available=True)
    reviews = item.reviews.filter(is_approved=True).select_related('user').order_by('-created_at')
    related_items = MenuItem.objects.filter(
        category=item.category, is_available=True
    ).exclude(pk=item.pk)[:4]
    return render(request, 'menu/item_detail.html', {
        'item': item,
        'reviews': reviews,
        'related_items': related_items,
    })


def menu_search(request):
    q = request.GET.get('q', '').strip()
    items = []
    if q and len(q) >= 2:
        qs = MenuItem.objects.filter(
            Q(name__icontains=q) | Q(description__icontains=q),
            is_available=True
        ).select_related('category')[:8]
        items = [
            {
                'id': item.id,
                'name': item.name,
                'price': str(item.price),
                'category__name': item.category.name,
                'slug': item.slug,
            }
            for item in qs
        ]
    return JsonResponse({'results': items, 'query': q})


def contact_submit(request):
    if request.method == 'POST':
        if is_rate_limited(request, 'contact', max_attempts=10, window_seconds=3600):
            return JsonResponse({'status': 'error', 'message': 'Too many messages sent. Please try again later.'}, status=429)
        record_attempt(request, 'contact', window_seconds=3600)
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid request format.'}, status=400)

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        if not name or not email or not message:
            return JsonResponse({'status': 'error', 'message': 'Please fill all required fields.'}, status=400)
        if '@' not in email:
            return JsonResponse({'status': 'error', 'message': 'Please enter a valid email.'}, status=400)

        ContactMessage.objects.create(
            name=name[:100],
            email=email[:254],
            phone=data.get('phone', '')[:20],
            subject=data.get('subject', 'General Inquiry')[:200],
            message=message,
        )
        return JsonResponse({'status': 'ok', 'message': "Message sent! We'll reply within 2 hours."})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)
