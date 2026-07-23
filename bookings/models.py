from django.db import models

class Booking(models.Model):
    STATUS_CHOICES = [
        ('active', 'Activa'),
        ('cancelled', 'Cancelada'),
    ]
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def save(self, *args, **kwargs):
        # 1. Base comisionable: (Ingreso Neto - Aseo) + Mascotas
        commissionable_base = self.net_revenue - self.cleaning_fee
        
        # 2. Obtener la tasa de la propiedad vinculada
        rate = self.listing.commission_rate
        
        # 3. Calcular montos (convertimos a int para eliminar decimales de la operación)
        self.staykeeper_revenue = round(commissionable_base * rate)
        self.owner_payout = round(commissionable_base * (1 - rate))
        
        super().save(*args, **kwargs)

class PendingBooking(models.Model):
    REASON_CHOICES = [
        ('OVERLAP', 'Solape de fechas'),
        ('LOW_CLEANING', 'Tarifa de limpieza baja'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmada como reserva'),
        ('cancelled', 'Marcada como cancelada'),
    ]

    reservation_code = models.CharField(max_length=100, unique=True)
    listing = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='pending_bookings')
    guest_name = models.CharField(max_length=200)
    check_in = models.DateField()
    check_out = models.DateField()
    net_revenue = models.IntegerField()
    cleaning_fee = models.IntegerField(default=0)
    pet_fee = models.IntegerField(default=0)

    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    overlap_group = models.CharField(max_length=255, blank=True)  # solo aplica si reason='OVERLAP'
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    detectado_en = models.DateTimeField(auto_now_add=True)
    resuelto_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-detectado_en']
        verbose_name = 'Reserva pendiente de revisión'
        verbose_name_plural = 'Reservas pendientes de revisión'

    def __str__(self):
        return f"{self.reservation_code} — {self.guest_name} [{self.get_reason_display()}] ({self.get_status_display()})"