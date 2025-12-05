from datetime import timedelta
from .models import Feriados


def calculate_business_days(initial_date, consecutive_days):
    """
    Calculate business days between initial_date and final_date.
    
    This function computes the number of business days (excluding weekends and 
    Brazilian holidays) in the range from initial_date (excluded) to final_date 
    (included), where final_date = initial_date + consecutive_days.
    
    Args:
        initial_date (date): Starting date (excluded from count)
        consecutive_days (int): Number of calendar days to add to initial_date
    
    Returns:
        int: Count of business days (excluding initial_date, including final_date)
    
    Examples:
        >>> from datetime import date
        >>> # Monday Jan 1 + 7 days = Monday Jan 8
        >>> # Count: Tue Jan 2, Wed Jan 3, Thu Jan 4, Fri Jan 5, Mon Jan 8
        >>> # (assuming no holidays, skipping Sat Jan 6, Sun Jan 7)
        >>> calculate_business_days(date(2024, 1, 1), 7)
        5
        
        >>> # Friday + 3 days = Monday
        >>> # Count: Saturday (skip), Sunday (skip), Monday (count)
        >>> calculate_business_days(date(2024, 1, 5), 3)
        1
    
    Notes:
        - Weekends are defined as Saturday (weekday=5) and Sunday (weekday=6)
        - Holidays are fetched from the Feriados model
        - The initial_date is NOT included in the count
        - The final_date IS included in the count (if it's a business day)
    """
    # Calculate the final date
    final_date = initial_date + timedelta(days=consecutive_days)
    
    # Handle edge case: if consecutive_days is 0 or negative
    if consecutive_days <= 0:
        return 0
    
    # Query holidays once for efficiency
    # Filter: date > initial_date AND date <= final_date
    holiday_dates = set(
        Feriados.objects.filter(
            date__gt=initial_date,
            date__lte=final_date
        ).values_list('date', flat=True)
    )
    
    # Count business days
    business_days_count = 0
    current_date = initial_date + timedelta(days=1)  # Start from day after initial_date
    
    # Iterate through each day in the range (excluding initial_date, including final_date)
    while current_date <= final_date:
        # Check if current_date is a business day
        is_weekend = current_date.weekday() in (5, 6)  # Saturday=5, Sunday=6
        is_holiday = current_date in holiday_dates
        
        if not is_weekend and not is_holiday:
            business_days_count += 1
        
        current_date += timedelta(days=1)
    
    return business_days_count
