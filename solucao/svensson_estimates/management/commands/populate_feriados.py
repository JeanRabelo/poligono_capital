import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from svensson_estimates.models import Feriados


class Command(BaseCommand):
    help = 'Populate Feriados model with dates from feriados.csv'

    def handle(self, *args, **options):
        # Get the path to the CSV file
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'feriados.csv'
        )
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'CSV file not found at {csv_path}'))
            return
        
        # Clear existing data
        deleted_count = Feriados.objects.all().count()
        Feriados.objects.all().delete()
        self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing holiday records'))
        
        # Read CSV and populate the model
        created_count = 0
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row and row[0]:  # Check if row is not empty
                    date_str = row[0].strip()
                    try:
                        # Parse Brazilian date format (dd/mm/yyyy)
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                        
                        # Create or update the Feriados entry
                        Feriados.objects.get_or_create(date=date_obj)
                        created_count += 1
                    except ValueError as e:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping invalid date: {date_str} - {e}')
                        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully populated {created_count} holiday dates')
        )
