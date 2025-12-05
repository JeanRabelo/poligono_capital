from datetime import date
from decimal import Decimal
import json
import math
from typing import Optional

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from rates.models import B3Rate
from .models import LinearAttempt
from .optimizers import OptimizationResult, optimize_parameters
from .utils import calculate_objective_function, calculate_calendar_days


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


def _serialize_attempt(attempt: LinearAttempt) -> dict:
    """Consistent representation of an attempt for JSON responses."""
    return {
        'id': attempt.id,
        'date': attempt.date.isoformat(),
        'beta0_initial': float(attempt.beta0_initial),
        'beta1_initial': float(attempt.beta1_initial),
        'beta2_initial': float(attempt.beta2_initial),
        'beta3_initial': float(attempt.beta3_initial),
        'lambda1_initial': float(attempt.lambda1_initial),
        'lambda2_initial': float(attempt.lambda2_initial),
        'beta0_final': float(attempt.beta0_final) if attempt.beta0_final else None,
        'beta1_final': float(attempt.beta1_final) if attempt.beta1_final else None,
        'beta2_final': float(attempt.beta2_final) if attempt.beta2_final else None,
        'beta3_final': float(attempt.beta3_final) if attempt.beta3_final else None,
        'lambda1_final': float(attempt.lambda1_final) if attempt.lambda1_final else None,
        'lambda2_final': float(attempt.lambda2_final) if attempt.lambda2_final else None,
        'rmse_initial': float(attempt.rmse_initial) if attempt.rmse_initial else None,
        'rmse_final': float(attempt.rmse_final) if attempt.rmse_final else None,
        'mae_initial': float(attempt.mae_initial) if attempt.mae_initial else None,
        'mae_final': float(attempt.mae_final) if attempt.mae_final else None,
        'r2_initial': float(attempt.r2_initial) if attempt.r2_initial else None,
        'r2_final': float(attempt.r2_final) if attempt.r2_final else None,
        'objective_function_initial': float(attempt.objective_function_initial) if attempt.objective_function_initial else None,
        'objective_function_final': float(attempt.objective_function_final) if attempt.objective_function_final else None,
        'observation': attempt.observation,
        'created_at': attempt.created_at.isoformat(),
    }


def list_attempts(request):
    """
    API endpoint to list all LinearAttempt records for a specific date.
    """
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Date parameter is required'}, status=400)
    
    try:
        selected_date = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    attempts = LinearAttempt.objects.filter(date=selected_date).order_by('-created_at')
    attempts_data = [_serialize_attempt(attempt) for attempt in attempts]
    return JsonResponse({'attempts': attempts_data})


@csrf_exempt
@require_http_methods(["POST"])
def create_attempt(request):
    """
    API endpoint to create a new LinearAttempt record.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Validate required fields
    required_fields = ['date', 'beta0_initial', 'beta1_initial', 'beta2_initial', 
                      'beta3_initial', 'lambda1_initial', 'lambda2_initial']
    for field in required_fields:
        if field not in data:
            return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
    
    try:
        attempt = LinearAttempt.objects.create(
            date=date.fromisoformat(data['date']),
            beta0_initial=Decimal(str(data['beta0_initial'])),
            beta1_initial=Decimal(str(data['beta1_initial'])),
            beta2_initial=Decimal(str(data['beta2_initial'])),
            beta3_initial=Decimal(str(data['beta3_initial'])),
            lambda1_initial=Decimal(str(data['lambda1_initial'])),
            lambda2_initial=Decimal(str(data['lambda2_initial'])),
            observation=data.get('observation', '')
        )
        
        return JsonResponse({
            'id': attempt.id,
            'message': 'LinearAttempt created successfully'
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def update_attempt(request, attempt_id):
    """
    API endpoint to update an existing LinearAttempt record.
    Only allows updating initial parameters and observation.
    """
    attempt = get_object_or_404(LinearAttempt, id=attempt_id)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Update only initial parameters and observation
    if 'beta0_initial' in data:
        attempt.beta0_initial = Decimal(str(data['beta0_initial']))
    if 'beta1_initial' in data:
        attempt.beta1_initial = Decimal(str(data['beta1_initial']))
    if 'beta2_initial' in data:
        attempt.beta2_initial = Decimal(str(data['beta2_initial']))
    if 'beta3_initial' in data:
        attempt.beta3_initial = Decimal(str(data['beta3_initial']))
    if 'lambda1_initial' in data:
        attempt.lambda1_initial = Decimal(str(data['lambda1_initial']))
    if 'lambda2_initial' in data:
        attempt.lambda2_initial = Decimal(str(data['lambda2_initial']))
    if 'observation' in data:
        attempt.observation = data['observation']
    
    try:
        attempt.save()
        return JsonResponse({'message': 'LinearAttempt updated successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_attempt(request, attempt_id):
    """
    API endpoint to delete a LinearAttempt record.
    """
    attempt = get_object_or_404(LinearAttempt, id=attempt_id)
    attempt.delete()
    return JsonResponse({'message': 'LinearAttempt deleted successfully'})


@csrf_exempt
@require_http_methods(["POST"])
def improve_attempt(request, attempt_id):
    """
    Improve a LinearAttempt by running an optimizer and overwriting final parameters when better.
    """
    attempt = get_object_or_404(LinearAttempt, id=attempt_id)

    # Parse optional payload (strategy selection)
    strategy = "local_search"
    try:
        payload = json.loads(request.body) if request.body else {}
        strategy = payload.get("strategy", strategy)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    use_final = (
        attempt.beta0_final is not None and attempt.beta1_final is not None and
        attempt.beta2_final is not None and attempt.beta3_final is not None and
        attempt.lambda1_final is not None and attempt.lambda2_final is not None
    )

    base_params = (
        float(attempt.beta0_final) if use_final else float(attempt.beta0_initial),
        float(attempt.beta1_final) if use_final else float(attempt.beta1_initial),
        float(attempt.beta2_final) if use_final else float(attempt.beta2_initial),
        float(attempt.beta3_final) if use_final else float(attempt.beta3_initial),
        float(attempt.lambda1_final) if use_final else float(attempt.lambda1_initial),
        float(attempt.lambda2_final) if use_final else float(attempt.lambda2_initial),
    )

    base_objective = attempt.objective_function_final if use_final else attempt.objective_function_initial
    if base_objective is None:
        base_objective = calculate_objective_function(attempt.date, *base_params)

    result: Optional[OptimizationResult] = None
    try:
        result = optimize_parameters(
            attempt.date,
            base_params,
            strategy_name=strategy,
        )
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    if result is None or result.best_objective is None:
        return JsonResponse({'error': 'Não foi possível melhorar esta tentativa'}, status=400)

    improved = base_objective is None or result.best_objective < base_objective
    if improved:
        attempt.beta0_final = Decimal(str(result.best_params[0]))
        attempt.beta1_final = Decimal(str(result.best_params[1]))
        attempt.beta2_final = Decimal(str(result.best_params[2]))
        attempt.beta3_final = Decimal(str(result.best_params[3]))
        attempt.lambda1_final = Decimal(str(result.best_params[4]))
        attempt.lambda2_final = Decimal(str(result.best_params[5]))
        attempt.save()
        attempt.refresh_from_db()

    response_payload = {
        'improved': improved,
        'previous_objective': float(base_objective) if base_objective is not None else None,
        'new_objective': float(result.best_objective),
        'strategy': result.strategy,
        'iterations': result.iterations,
        'attempt': _serialize_attempt(attempt),
    }

    status_code = 200 if improved else 202
    return JsonResponse(response_payload, status=status_code)


@require_http_methods(["GET"])
def get_svensson_curve(request, attempt_id):
    """
    API endpoint to calculate the Svensson curve for a specific attempt.
    Returns the curve data points.
    """
    attempt = get_object_or_404(LinearAttempt, id=attempt_id)
    
    # Check if we should use final or initial parameters
    use_final = (
        attempt.beta0_final is not None and attempt.beta1_final is not None and 
        attempt.beta2_final is not None and attempt.beta3_final is not None and 
        attempt.lambda1_final is not None and attempt.lambda2_final is not None
    )
    
    if use_final:
        beta0 = float(attempt.beta0_final)
        beta1 = float(attempt.beta1_final)
        beta2 = float(attempt.beta2_final)
        beta3 = float(attempt.beta3_final)
        lambda1 = float(attempt.lambda1_final)
        lambda2 = float(attempt.lambda2_final)
        params_type = 'final'
    else:
        beta0 = float(attempt.beta0_initial)
        beta1 = float(attempt.beta1_initial)
        beta2 = float(attempt.beta2_initial)
        beta3 = float(attempt.beta3_initial)
        lambda1 = float(attempt.lambda1_initial)
        lambda2 = float(attempt.lambda2_initial)
        params_type = 'initial'
    
    # Calculate Svensson curve for a range of maturities (in years)
    # We'll generate points from 1 to 30 years with fine granularity
    curve_data = []
    
    # Generate points: every day for first year, then every 7 days up to 10 years, then every 21 days
    days_list = list(range(1, 253))  # Daily for first year (252 days)
    days_list.extend(range(259, 2521, 7))  # Weekly for years 1-10
    days_list.extend(range(2527, 10951, 21))  # Monthly for years 10-30
    
    for t in days_list:
        tau = t / 252  # Convert days to years (252 trading days per year)
        
        # Svensson formula
        try:
            term1 = beta0/100.0
            term2 = beta1/100.0 * ((1 - math.exp(-tau * lambda1)) / (tau * lambda1))
            term3 = beta2/100.0 * (((1 - math.exp(-tau * lambda1)) / (tau * lambda1)) - math.exp(-tau * lambda1))
            term4 = beta3/100.0 * (((1 - math.exp(-tau * lambda2)) / (tau * lambda2)) - math.exp(-tau * lambda2))
            
            y = term1 + term2 + term3 + term4
            
            curve_data.append({
                'dias_corridos': calculate_calendar_days(attempt.date, t),
                'taxa': round(y, 6)
            })
        except (ZeroDivisionError, OverflowError):
            continue
    
    return JsonResponse({
        'curve': curve_data,
        'params_type': params_type
    })
