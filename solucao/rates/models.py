from django.db import models


class B3Rate(models.Model):
    """Model to store B3 reference rates."""
    date = models.DateField()
    indicator = models.CharField(max_length=200)
    value = models.DecimalField(max_digits=12, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date', 'indicator']
        unique_together = ['date', 'indicator']
    
    def __str__(self):
        return f"{self.date} - {self.indicator}: {self.value}"

