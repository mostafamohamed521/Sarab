from django.contrib import admin
from .models import Review, Wishlist


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'menu_item', 'rating', 'is_approved', 'created_at']
    list_editable = ['is_approved']
    list_filter = ['rating', 'is_approved']
