from django.db import models


class B3Rate(models.Model):
    """Model to store B3 DI x PRE reference rates."""
    date = models.DateField()
    dias_corridos = models.IntegerField(help_text="Dias corridos")
    di_pre_252 = models.DecimalField(max_digits=12, decimal_places=6, help_text="DI x PRE 252")
    di_pre_360 = models.DecimalField(max_digits=12, decimal_places=6, help_text="DI x PRE 360")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date', 'dias_corridos']
        unique_together = ['date', 'dias_corridos']
    
    def __str__(self):
        return f"{self.date} - {self.dias_corridos} dias: {self.di_pre_252}% / {self.di_pre_360}%"

