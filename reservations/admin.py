from django.contrib import admin
from .models import Reservation, Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'capacity', 'location', 'is_active']
    list_editable = ['is_active']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['confirmation_code', 'full_name', 'date', 'time', 'guests', 'status']
    list_filter = ['status', 'date']
    search_fields = ['full_name', 'email', 'confirmation_code']
    list_editable = ['status']
