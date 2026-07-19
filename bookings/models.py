from django.db import models

class Booking(models.Model):
    reservation_code = models.CharField(max_length=100, unique=True)
    listing = models.ForeignKey('properties.Property', on_delete=models.CASCADE)
    guest = models.ForeignKey('guests.Guest', on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    
    # Montos base (Integrer para CLP)
    net_revenue = models.IntegerField()  # Lo que recibes de la plataforma
    cleaning_fee = models.IntegerField(default=0)
    pet_fee = models.IntegerField(default=0)
    platform = models.CharField(max_length=50, blank=True, null=True)

    # Montos calculados
    owner_payout = models.IntegerField(editable=False)
    staykeeper_revenue = models.IntegerField(editable=False)

    def save(self, *args, **kwargs):
        # 1. Base comisionable: (Ingreso Neto - Aseo) + Mascotas
        commissionable_base = self.net_revenue - self.cleaning_fee
        
        # 2. Obtener la tasa de la propiedad vinculada
        rate = self.listing.commission_rate
        
        # 3. Calcular montos (convertimos a int para eliminar decimales de la operación)
        self.staykeeper_revenue = round(commissionable_base * rate)
        self.owner_payout = round(commissionable_base * (1 - rate))
        
        super().save(*args, **kwargs)