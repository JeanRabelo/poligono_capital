from django.shortcuts import render
from django.http import JsonResponse
from rates.models import B3Rate
from datetime import date


def homepage(request):
    """
    Homepage view for Svensson estimates.
    Shows a list of available dates and chart data when selected.
    """
    # Get all unique dates from B3Rate, ordered by date descending (newest first)
    available_dates = B3Rate.objects.values('date').distinct().order_by('-date')
    
    selected_date = None
    rates_data = None
    
    # Check if a date was selected (via GET parameter)
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = date.fromisoformat(date_str)
            # Get rates for the selected date (only DI x PRE 252)
            rates = B3Rate.objects.filter(date=selected_date).order_by('dias_corridos')
            if rates.exists():
                rates_data = rates
        except (ValueError, TypeError):
            pass
    
    context = {
        'available_dates': available_dates,
        'selected_date': selected_date,
        'rates_data': rates_data,
    }
    
    return render(request, 'svensson_estimates/homepage.html', context)
