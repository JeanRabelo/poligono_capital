from django.contrib import admin
from .models import B3Rate


@admin.register(B3Rate)
class B3RateAdmin(admin.ModelAdmin):
    list_display = ['date', 'dias_corridos', 'di_pre_252', 'di_pre_360', 'created_at']
    list_filter = ['date', 'created_at']
    search_fields = ['dias_corridos']
    date_hierarchy = 'date'

