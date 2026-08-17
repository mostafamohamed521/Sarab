from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Address, NewsletterSubscriber
from config import admin_dashboard  # noqa: F401 — side effects only, see that module's docstring


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('phone', 'avatar', 'role', 'date_of_birth', 'bio', 'email_verified')}),
    )

    def get_readonly_fields(self, request, obj=None):
        # Django's stock UserAdmin lets anyone with change-user access
        # edit is_superuser/is_staff/groups/user_permissions on ANY
        # account, including their own — a non-superuser staff member
        # with admin access could grant themselves full superuser
        # rights. Since this project already has a real customer/
        # staff/admin role distinction, that gap defeats it. Only
        # superusers can grant/revoke superuser status, staff status,
        # or permission groups; everyone else with access to this page
        # can still manage ordinary account fields.
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly += ['is_superuser', 'is_staff', 'groups', 'user_permissions', 'role']
        return readonly


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'city', 'is_default']
    list_filter = ['label', 'is_default']


@admin.register(NewsletterSubscriber)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at', 'is_active']
