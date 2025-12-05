from datetime import timedelta
from .models import Feriados
from rates.models import B3Rate
import math
from decimal import Decimal


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


def calculate_rmse(date, beta0, beta1, beta2, beta3, lambda1, lambda2):
    """
    Calculate RMSE (Root Mean Square Error) for Svensson model parameters.
    
    This function calculates the RMSE between real prices from B3 rates and 
    calculated prices from the Svensson model with the given parameters.
    
    Args:
        date (date): Date for which to fetch B3 rates
        beta0 (float): Svensson parameter β0
        beta1 (float): Svensson parameter β1
        beta2 (float): Svensson parameter β2
        beta3 (float): Svensson parameter β3
        lambda1 (float): Svensson parameter λ1
        lambda2 (float): Svensson parameter λ2
    
    Returns:
        Decimal: RMSE value, or None if calculation fails
    
    Formula:
        RMSE = sqrt((1/n) * sum((price_error)^2))
        price_error = real_price - calculated_price
        real_price = 1/(1+tx_anual_B3_252)^(periodos_de_anos_de_252_dias)
        calculated_price = 1/(1+tx_anual_calculada)^(periodos_de_anos_de_252_dias)
        periodos_de_anos_de_252_dias = calculate_business_days(date, dias_corridos) / 252
    """
    try:
        # Fetch all B3Rate records for the given date
        b3_rates = B3Rate.objects.filter(date=date).order_by('dias_corridos')
        
        if not b3_rates.exists():
            return None
        
        squared_errors = []
        
        for rate in b3_rates:
            # Calculate periods in years (252 business days)
            business_days = calculate_business_days(date, rate.dias_corridos)
            periodos_de_anos_de_252_dias = business_days / 252.0
            
            # Skip if no business days (edge case)
            if periodos_de_anos_de_252_dias <= 0:
                continue
            
            # Calculate real price from B3 rate
            # di_pre_252 is in percentage, so we divide by 100
            tx_anual_B3_252 = float(rate.di_pre_252) / 100.0
            real_price = 1.0 / ((1.0 + tx_anual_B3_252) ** periodos_de_anos_de_252_dias)
            
            # Calculate Svensson rate (tau = periodos_de_anos_de_252_dias)
            tau = periodos_de_anos_de_252_dias
            
            # Svensson formula
            try:
                term1 = beta0/100.0
                term2 = beta1/100.0 * ((1 - math.exp(-tau * lambda1)) / (tau * lambda1))
                term3 = beta2/100.0 * (((1 - math.exp(-tau * lambda1)) / (tau * lambda1)) - math.exp(-tau * lambda1))
                term4 = beta3/100.0 * (((1 - math.exp(-tau * lambda2)) / (tau * lambda2)) - math.exp(-tau * lambda2))
                
                tx_anual_calculada = term1 + term2 + term3 + term4
                
                # tx_anual_calculada is already in decimal form (not percentage)
                # so we use it directly
                calculated_price = 1.0 / ((1.0 + tx_anual_calculada) ** periodos_de_anos_de_252_dias)
                
                # Calculate price error
                price_error = real_price - calculated_price
                squared_errors.append(price_error ** 2)
                
            except (ZeroDivisionError, OverflowError, ValueError):
                # Skip this point if calculation fails
                continue
        
        # Calculate RMSE
        if len(squared_errors) == 0:
            return None
        
        mean_squared_error = sum(squared_errors) / len(squared_errors)
        rmse = math.sqrt(mean_squared_error)
        
        return Decimal(str(rmse))
        
    except Exception as e:
        # Log the error or handle it appropriately
        print(f"Error calculating RMSE: {e}")
        return None


def calculate_mae(date, beta0, beta1, beta2, beta3, lambda1, lambda2):
    """
    Calculate MAE (Mean Absolute Error) for Svensson model parameters.
    
    This function calculates the MAE between real prices from B3 rates and 
    calculated prices from the Svensson model with the given parameters.
    
    Args:
        date (date): Date for which to fetch B3 rates
        beta0 (float): Svensson parameter β0
        beta1 (float): Svensson parameter β1
        beta2 (float): Svensson parameter β2
        beta3 (float): Svensson parameter β3
        lambda1 (float): Svensson parameter λ1
        lambda2 (float): Svensson parameter λ2
    
    Returns:
        Decimal: MAE value, or None if calculation fails
    
    Formula:
        MAE = (1/n) * sum(|price_error|)
        price_error = real_price - calculated_price
        real_price = 1/(1+tx_anual_B3_252)^(periodos_de_anos_de_252_dias)
        calculated_price = 1/(1+tx_anual_calculada)^(periodos_de_anos_de_252_dias)
        periodos_de_anos_de_252_dias = calculate_business_days(date, dias_corridos) / 252
    """
    try:
        # Fetch all B3Rate records for the given date
        b3_rates = B3Rate.objects.filter(date=date).order_by('dias_corridos')
        
        if not b3_rates.exists():
            return None
        
        absolute_errors = []
        
        for rate in b3_rates:
            # Calculate periods in years (252 business days)
            business_days = calculate_business_days(date, rate.dias_corridos)
            periodos_de_anos_de_252_dias = business_days / 252.0
            
            # Skip if no business days (edge case)
            if periodos_de_anos_de_252_dias <= 0:
                continue
            
            # Calculate real price from B3 rate
            # di_pre_252 is in percentage, so we divide by 100
            tx_anual_B3_252 = float(rate.di_pre_252) / 100.0
            real_price = 1.0 / ((1.0 + tx_anual_B3_252) ** periodos_de_anos_de_252_dias)
            
            # Calculate Svensson rate (tau = periodos_de_anos_de_252_dias)
            tau = periodos_de_anos_de_252_dias
            
            # Svensson formula
            try:
                term1 = beta0/100.0
                term2 = beta1/100.0 * ((1 - math.exp(-tau * lambda1)) / (tau * lambda1))
                term3 = beta2/100.0 * (((1 - math.exp(-tau * lambda1)) / (tau * lambda1)) - math.exp(-tau * lambda1))
                term4 = beta3/100.0 * (((1 - math.exp(-tau * lambda2)) / (tau * lambda2)) - math.exp(-tau * lambda2))
                
                tx_anual_calculada = term1 + term2 + term3 + term4
                
                # tx_anual_calculada is already in decimal form (not percentage)
                # so we use it directly
                calculated_price = 1.0 / ((1.0 + tx_anual_calculada) ** periodos_de_anos_de_252_dias)
                
                # Calculate price error
                price_error = real_price - calculated_price
                absolute_errors.append(abs(price_error))
                
            except (ZeroDivisionError, OverflowError, ValueError):
                # Skip this point if calculation fails
                continue
        
        # Calculate MAE
        if len(absolute_errors) == 0:
            return None
        
        mae = sum(absolute_errors) / len(absolute_errors)
        
        return Decimal(str(mae))
        
    except Exception as e:
        # Log the error or handle it appropriately
        print(f"Error calculating MAE: {e}")
        return None

def calculate_r2(date, beta0, beta1, beta2, beta3, lambda1, lambda2):
    """
    Calculate R² (Coefficient of Determination) for Svensson model parameters.

    R² = 1 - (SS_res / SS_tot)
    SS_res = sum((y - y_hat)^2)
    SS_tot = sum((y - y_mean)^2)

    Where:
        y      = real_price (from B3 rate)
        y_hat  = calculated_price (from Svensson model)
    """
    try:
        b3_rates = B3Rate.objects.filter(date=date).order_by('dias_corridos')

        if not b3_rates.exists():
            return None

        real_values = []
        predicted_values = []

        for rate in b3_rates:
            business_days = calculate_business_days(date, rate.dias_corridos)
            periodos_de_anos_de_252_dias = business_days / 252.0

            if periodos_de_anos_de_252_dias <= 0:
                continue

            tx_anual_B3_252 = float(rate.di_pre_252) / 100.0
            real_price = 1.0 / ((1.0 + tx_anual_B3_252) ** periodos_de_anos_de_252_dias)

            tau = periodos_de_anos_de_252_dias

            try:
                term1 = beta0/100.0
                term2 = beta1/100.0 * ((1 - math.exp(-tau * lambda1)) / (tau * lambda1))
                term3 = beta2/100.0 * (((1 - math.exp(-tau * lambda1)) / (tau * lambda1)) - math.exp(-tau * lambda1))
                term4 = beta3/100.0 * (((1 - math.exp(-tau * lambda2)) / (tau * lambda2)) - math.exp(-tau * lambda2))

                tx_anual_calculada = term1 + term2 + term3 + term4
                calculated_price = 1.0 / ((1.0 + tx_anual_calculada) ** periodos_de_anos_de_252_dias)

                real_values.append(real_price)
                predicted_values.append(calculated_price)

            except (ZeroDivisionError, OverflowError, ValueError):
                continue

        if len(real_values) < 2:
            return None

        y_mean = sum(real_values) / len(real_values)

        ss_res = 0.0
        ss_tot = 0.0
        for y, y_hat in zip(real_values, predicted_values):
            diff_res = y - y_hat
            ss_res += diff_res * diff_res

            diff_tot = y - y_mean
            ss_tot += diff_tot * diff_tot

        if ss_tot == 0.0:
            # Todos os y iguais => R² indefinido (não há variância a explicar)
            return None

        r2 = 1.0 - (ss_res / ss_tot)
        return Decimal(str(r2))

    except Exception as e:
        print(f"Error calculating R²: {e}")
        return None

def calculate_objective_function(date, beta0, beta1, beta2, beta3, lambda1, lambda2):
    """
    Calculate the objective function:
        objective_function = sum( (1/consecutive_days) * (price_error)^2 )

    Where:
        price_error = real_price - calculated_price
        consecutive_days = rate.dias_corridos (consecutive days)
    """
    try:
        b3_rates = B3Rate.objects.filter(date=date).order_by('dias_corridos')

        if not b3_rates.exists():
            return None

        total = 0.0
        used_points = 0

        for rate in b3_rates:
            # Evitar divisão por zero ou pesos inválidos
            if not rate.dias_corridos or rate.dias_corridos <= 0:
                continue

            business_days = calculate_business_days(date, rate.dias_corridos)
            periodos_de_anos_de_252_dias = business_days / 252.0

            if periodos_de_anos_de_252_dias <= 0:
                continue

            # Preço "real" (B3)
            tx_anual_B3_252 = float(rate.di_pre_252) / 100.0
            real_price = 1.0 / ((1.0 + tx_anual_B3_252) ** periodos_de_anos_de_252_dias)
            tau = periodos_de_anos_de_252_dias

            try:
                # Svensson
                term1 = beta0/100.0
                term2 = beta1/100.0 * ((1 - math.exp(-tau * lambda1)) / (tau * lambda1))
                term3 = beta2/100.0 * (((1 - math.exp(-tau * lambda1)) / (tau * lambda1)) - math.exp(-tau * lambda1))
                term4 = beta3/100.0 * (((1 - math.exp(-tau * lambda2)) / (tau * lambda2)) - math.exp(-tau * lambda2))

                tx_anual_calculada = term1 + term2 + term3 + term4
                calculated_price = 1.0 / ((1.0 + tx_anual_calculada) ** periodos_de_anos_de_252_dias)
                price_error = real_price - calculated_price
                weight = 1.0 / float(rate.dias_corridos)
                total += weight * (price_error ** 2)
                used_points += 1

            except (ZeroDivisionError, OverflowError, ValueError):
                continue

        if used_points == 0:
            return None

        return Decimal(str(total))

    except Exception as e:
        print(f"Error calculating função_objetivo: {e}")
        return None
