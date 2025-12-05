from django.db import models


class Feriados(models.Model):
    """Model to store Brazilian holiday dates."""
    date = models.DateField(unique=True, help_text="Holiday date")
    
    class Meta:
        ordering = ['date']
        verbose_name = "Feriado"
        verbose_name_plural = "Feriados"
    
    def __str__(self):
        return f"Feriado: {self.date.strftime('%d/%m/%Y')}"


class LinearAttempt(models.Model):
    """Model to store linear attempts for Svensson parameter estimation."""
    date = models.DateField(help_text="Date associated with this estimation attempt")
    
    # Initial parameters (6 parameters of the Svensson model)
    beta0_initial = models.DecimalField(max_digits=15, decimal_places=8, help_text="Initial β0")
    beta1_initial = models.DecimalField(max_digits=15, decimal_places=8, help_text="Initial β1")
    beta2_initial = models.DecimalField(max_digits=15, decimal_places=8, help_text="Initial β2")
    beta3_initial = models.DecimalField(max_digits=15, decimal_places=8, help_text="Initial β3")
    lambda1_initial = models.DecimalField(max_digits=15, decimal_places=8, help_text="Initial λ1")
    lambda2_initial = models.DecimalField(max_digits=15, decimal_places=8, help_text="Initial λ2")
    
    # Final parameters (6 parameters of the Svensson model after estimation)
    beta0_final = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="Final β0")
    beta1_final = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="Final β1")
    beta2_final = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="Final β2")
    beta3_final = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="Final β3")
    lambda1_final = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="Final λ1")
    lambda2_final = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="Final λ2")
    
    # Error metrics
    rmse_initial = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="RMSE for initial parameters")
    rmse_final = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="RMSE for final parameters")
    mae_initial = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="MAE for initial parameters")
    mae_final = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True, help_text="MAE for final parameters")
    
    # Observation field
    observation = models.TextField(blank=True, help_text="Notes about this estimation attempt")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Linear Attempt"
        verbose_name_plural = "Linear Attempts"
    
    def __str__(self):
        return f"Svensson Attempt for {self.date}"
