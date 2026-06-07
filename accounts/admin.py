from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Address, NewsletterSubscriber


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('phone', 'avatar', 'role', 'date_of_birth', 'bio', 'email_verified')}),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'city', 'is_default']
    list_filter = ['label', 'is_default']


@admin.register(NewsletterSubscriber)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at', 'is_active']
