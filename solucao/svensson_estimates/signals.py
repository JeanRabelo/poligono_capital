import csv
import os
from datetime import datetime
from django.db.models.signals import post_migrate
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
