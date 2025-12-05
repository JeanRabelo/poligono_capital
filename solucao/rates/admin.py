from django.contrib import admin
from .models import B3Rate


@admin.register(B3Rate)
class B3RateAdmin(admin.ModelAdmin):
    list_display = ['date', 'indicator', 'value', 'created_at']
    list_filter = ['date', 'created_at']
    search_fields = ['indicator']
    date_hierarchy = 'date'

