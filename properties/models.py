from django.db import models
from django.conf import settings

class Property(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    airbnb_ical_url = models.URLField(max_length=500, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.15)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Properties"