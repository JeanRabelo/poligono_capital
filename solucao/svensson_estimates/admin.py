from django.contrib import admin
from .models import LinearAttempt, Feriados


@admin.register(Feriados)
class FeriadosAdmin(admin.ModelAdmin):
    list_display = ('date',)
    list_filter = ('date',)
    search_fields = ('date',)
    date_hierarchy = 'date'


@admin.register(LinearAttempt)
class LinearAttemptAdmin(admin.ModelAdmin):
    list_display = ('date', 'created_at', 'beta0_final', 'beta1_final')
    list_filter = ('date', 'created_at')
    search_fields = ('date', 'observation')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Date Information', {
            'fields': ('date',)
        }),
        ('Initial Parameters', {
            'fields': ('beta0_initial', 'beta1_initial', 'beta2_initial', 
                      'beta3_initial', 'lambda1_initial', 'lambda2_initial')
        }),
        ('Final Parameters', {
            'fields': ('beta0_final', 'beta1_final', 'beta2_final', 
                      'beta3_final', 'lambda1_final', 'lambda2_final')
        }),
        ('Notes', {
            'fields': ('observation',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
