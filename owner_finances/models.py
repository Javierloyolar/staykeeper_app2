from django.db import models
from django.core.exceptions import ValidationError
from datetime import date

class OwnerFinancialTransaction(models.Model):

    TYPE_CHOICES = [
        ('income',  'Ingreso'),
        ('expense', 'Egreso'),
    ]
    CATEGORY_CHOICES = [
        ('late_checkout',      'Late Checkout'),
        ('early_checkin',      'Early Check-in'),
        ('repair',             'Reparación'),
        ('supply',             'Insumos'),
        ('guest_compensation', 'Compensación Huésped'),
        ('utilities',          'Servicios'),
        ('maintenance',        'Mantención'),
        ('other',              'Otro'),
    ]
    IMPACT_CHOICES = [
        ('full_owner', '100% Propietario'),
        ('full_admin', '100% Staykeeper'),
        ('mixed',      'Mixto (aplica comisión)'),
    ]

    listing          = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='owner_transactions')
    booking          = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='owner_transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category         = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    amount           = models.IntegerField()  # siempre positivo
    owner_impact     = models.CharField(max_length=15, choices=IMPACT_CHOICES)
    description      = models.TextField(blank=True)
    transaction_date = models.DateField()
    created_at       = models.DateTimeField(auto_now_add=True)

    @property
    def owner_share(self): # monto que afecta al cliente propietario, considerando tipo, impacto y comisión
        
        factor = -1 if self.transaction_type == 'expense' else 1
        monto_con_signo = self.amount * factor

        if self.owner_impact == 'full_owner':
            return monto_con_signo
        if self.owner_impact == 'full_admin':
            return 0
        if self.owner_impact == 'mixed':
            return int(monto_con_signo * (1 - self.listing.commission_rate))
        return 0

    @property # monto que afecta al administrador (comisión)
    def admin_share(self):
        factor = -1 if self.transaction_type == 'expense' else 1
        monto_con_signo = self.amount * factor
        return monto_con_signo - self.owner_share

    def save(self, *args, **kwargs):
        # Inmutabilidad: una vez guardada no se puede modificar
        if self.pk:
            raise ValidationError(
                "Las transacciones no pueden modificarse. Para corregir, crea una transacción compensatoria con el tipo u impacto inverso."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        reserva = self.booking.reservation_code if self.booking else 'Sin reserva'
        signo = "+" if self.transaction_type == 'income' else "-"
        return f"{self.listing.name} — {self.get_category_display()} ({reserva}) {signo}${self.amount}"

    class Meta:
        ordering = ['-transaction_date']
        verbose_name = 'Transacción Financiera'
        verbose_name_plural = 'Transacciones Financieras'


class OwnerPayout(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('paid',    'Pagado'),
    ]

    booking          = models.OneToOneField('bookings.Booking', on_delete=models.CASCADE, related_name='payout')
    base_amount      = models.IntegerField()  # snapshot de booking.owner_payout al crear
    property_charges = models.ManyToManyField(  # gastos de propiedad agregados manualmente
        OwnerFinancialTransaction,
        blank=True,
        related_name='included_in_payouts'
    )
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    scheduled_date   = models.DateField()
    paid_date        = models.DateField(null=True, blank=True)
    payment_method   = models.CharField(max_length=100, default='Transferencia Bancaria', blank=True)
    notes            = models.TextField(blank=True)

    @property
    def booking_transactions_total(self):
        # Automático: Como owner_share ya maneja su propio signo (+/-), solo sumamos directamente
        txs = self.booking.owner_transactions.all()
        return sum(t.owner_share for t in txs)

    @property
    def property_charges_total(self):
       # Manual: Los gastos de propiedad ya retornan como valores negativos en owner_share
        return sum(t.owner_share for t in self.property_charges.all())
    
    @property
    def net_amount(self):
        # Suma algebraica limpia de la estadía base y todas las transacciones asociadas
        return self.base_amount + self.booking_transactions_total + self.property_charges_total

    def mark_as_paid(self, payment_method=None, paid_date=None):
        self.status = 'paid'
        if payment_method:
            self.payment_method = payment_method
        self.paid_date = paid_date or date.today()
        self.save()

    def __str__(self):
        reserva = self.booking.reservation_code if self.booking else 'Sin Código'
        return f"Payout {reserva} — {self.get_status_display()} ${self.net_amount}"

    class Meta:
        ordering = ['-scheduled_date']
        verbose_name = 'Pago a Propietario'
        verbose_name_plural = 'Pagos a Propietarios'