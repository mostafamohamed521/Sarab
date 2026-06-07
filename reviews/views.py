from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
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
    rating = int(data.get('rating', 5))
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
    return render(request, 'reviews/wishlist.html', {'wishlist': wishlist})


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
