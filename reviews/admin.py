from django.contrib import admin
from .models import Review, Wishlist


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'menu_item', 'rating', 'is_approved', 'created_at']
    list_editable = ['is_approved']
    list_filter = ['rating', 'is_approved']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    # Wishlist was imported here but never actually registered — staff
    # had no way to see which items customers are wishlisting at all.
    list_display = ['user', 'item_count', 'created_at']
    search_fields = ['user__email']
    filter_horizontal = ['items']

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'
