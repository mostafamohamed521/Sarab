from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count
from .models import Review, Wishlist
from menu.models import MenuItem
import json


@login_required
@require_POST
def add_review(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except Exception:
        data = request.POST
    try:
        rating = int(data.get('rating', 5))
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Rating must be a number.'}, status=400)
    if rating < 1 or rating > 5:
        return JsonResponse({'status': 'error', 'message': 'Rating must be between 1 and 5.'}, status=400)
    comment = data.get('comment', '').strip()
    if not comment:
        return JsonResponse({'status': 'error', 'message': 'Comment is required.'}, status=400)
    review, created = Review.objects.update_or_create(
        menu_item=item, user=request.user,
        defaults={'rating': rating, 'comment': comment, 'title': data.get('title', '')}
    )
    return JsonResponse({'status': 'ok', 'message': 'Review submitted!', 'created': created})


@login_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    items = wishlist.items.select_related('category').prefetch_related('tags').annotate(
        _avg_rating=Avg('reviews__rating'), _review_count=Count('reviews', distinct=True)
    )
    return render(request, 'reviews/wishlist.html', {'wishlist': wishlist, 'wishlist_items': items})


@login_required
@require_POST
def toggle_wishlist(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    if item in wishlist.items.all():
        wishlist.items.remove(item)
        added = False
    else:
        wishlist.items.add(item)
        added = True
    return JsonResponse({'status': 'ok', 'added': added, 'count': wishlist.items.count()})
