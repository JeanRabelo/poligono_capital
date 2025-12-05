import csv
import os
from datetime import datetime
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.apps import apps


@receiver(post_migrate)
def populate_feriados(sender, **kwargs):
    """
    Automatically populate Feriados model with dates from feriados.csv after migrations.
    This runs only once when the table is empty.
    """
    # Only run for the svensson_estimates app
    if sender.name != 'svensson_estimates':
        return
    
    # Get the Feriados model
    Feriados = apps.get_model('svensson_estimates', 'Feriados')
    
    # Check if table is already populated
    if Feriados.objects.exists():
        return
    
    # Get the path to the CSV file
    csv_path = os.path.join(
        os.path.dirname(__file__),
        'feriados.csv'
    )
    
    if not os.path.exists(csv_path):
        print(f'Warning: feriados.csv not found at {csv_path}')
        return
    
    # Read CSV and populate the model
    created_count = 0
    print('Populating Feriados model from feriados.csv...')
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row and row[0]:  # Check if row is not empty
                date_str = row[0].strip()
                try:
                    # Parse Brazilian date format (dd/mm/yyyy)
                    date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                    
                    # Create the Feriados entry
                    Feriados.objects.get_or_create(date=date_obj)
                    created_count += 1
                except ValueError as e:
                    print(f'Warning: Skipping invalid date: {date_str} - {e}')
    
    print(f'Successfully populated {created_count} holiday dates')


@receiver(post_save, sender='svensson_estimates.LinearAttempt')
def calculate_rmse_on_save(sender, instance, created, **kwargs):
    """
    Automatically calculate RMSE and MAE values when a LinearAttempt is created or updated.
    Calculates rmse_initial and mae_initial for initial parameters.
    Calculates rmse_final and mae_final for final parameters.
    """
    from .models import LinearAttempt
    from .utils import calculate_rmse, calculate_mae
    
    # Flag to check if we need to update
    needs_update = False
    
    # Calculate RMSE for initial parameters
    rmse_initial = calculate_rmse(
        instance.date,
        float(instance.beta0_initial),
        float(instance.beta1_initial),
        float(instance.beta2_initial),
        float(instance.beta3_initial),
        float(instance.lambda1_initial),
        float(instance.lambda2_initial)
    )
    
    if rmse_initial is not None and instance.rmse_initial != rmse_initial:
        instance.rmse_initial = rmse_initial
        needs_update = True
    
    # Calculate MAE for initial parameters
    mae_initial = calculate_mae(
        instance.date,
        float(instance.beta0_initial),
        float(instance.beta1_initial),
        float(instance.beta2_initial),
        float(instance.beta3_initial),
        float(instance.lambda1_initial),
        float(instance.lambda2_initial)
    )
    
    if mae_initial is not None and instance.mae_initial != mae_initial:
        instance.mae_initial = mae_initial
        needs_update = True
    
    # Calculate RMSE and MAE for final parameters if they exist
    has_final = (
        instance.beta0_final is not None and instance.beta1_final is not None and 
        instance.beta2_final is not None and instance.beta3_final is not None and 
        instance.lambda1_final is not None and instance.lambda2_final is not None
    )
    
    if has_final:
        rmse_final = calculate_rmse(
            instance.date,
            float(instance.beta0_final),
            float(instance.beta1_final),
            float(instance.beta2_final),
            float(instance.beta3_final),
            float(instance.lambda1_final),
            float(instance.lambda2_final)
        )
        
        if rmse_final is not None and instance.rmse_final != rmse_final:
            instance.rmse_final = rmse_final
            needs_update = True
        
        mae_final = calculate_mae(
            instance.date,
            float(instance.beta0_final),
            float(instance.beta1_final),
            float(instance.beta2_final),
            float(instance.beta3_final),
            float(instance.lambda1_final),
            float(instance.lambda2_final)
        )
        
        if mae_final is not None and instance.mae_final != mae_final:
            instance.mae_final = mae_final
            needs_update = True
    else:
        # Clear rmse_final and mae_final if final parameters are not complete
        if instance.rmse_final is not None:
            instance.rmse_final = None
            needs_update = True
        if instance.mae_final is not None:
            instance.mae_final = None
            needs_update = True
    
    # Save only if we calculated new RMSE or MAE values
    # Avoid infinite recursion by disconnecting the signal temporarily
    if needs_update:
        post_save.disconnect(calculate_rmse_on_save, sender=LinearAttempt)
        instance.save(update_fields=['rmse_initial', 'rmse_final', 'mae_initial', 'mae_final'])
        post_save.connect(calculate_rmse_on_save, sender=LinearAttempt)
