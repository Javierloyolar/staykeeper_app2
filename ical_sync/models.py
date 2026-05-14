from django.db import models
from properties.models import Property

class IcalBlock(models.Model):
    listing = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='ical_blocks')
    check_in = models.DateField()
    check_out = models.DateField()
    is_reservation = models.BooleanField(default=False)  # True = Reserva, False = Bloqueado
    external_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        tipo = "Reserva" if self.is_reservation else "Bloqueo"
        return f"{self.listing.name}: {tipo} ({self.check_in})"