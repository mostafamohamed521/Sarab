from django.contrib import admin
from .models import Category, MenuItem, MenuItemVariation, MenuItemAddon, Tag, ContactMessage


class VariationInline(admin.TabularInline):
    model = MenuItemVariation
    extra = 1


class AddonInline(admin.TabularInline):
    model = MenuItemAddon
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'order', 'item_count']
    list_editable = ['is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available', 'is_featured', 'badge']
    list_filter = ['category', 'is_available', 'is_featured', 'badge']
    list_editable = ['is_available', 'is_featured']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [VariationInline, AddonInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_read']
    list_editable = ['is_read']
