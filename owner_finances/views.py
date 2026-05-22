from django.views.generic import DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import OwnerPayout

class OwnerPayoutDetailView(LoginRequiredMixin, DetailView):
    """
    Vista detallada para la colilla de liquidación que ve el propietario.
    """
    model = OwnerPayout
    template_name = 'owner_finances/liquidacion_detalle.html'
    context_object_name = 'payout'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payout = self.get_object()

        # Desglose matemático limpio para los bloques del template HTML
        context['base_amount'] = payout.base_amount
        
        # Extras automáticos del huésped (Tienen el booking amarrado)
        context['booking_transactions'] = payout.booking.owner_transactions.all()
        context['booking_transactions_total'] = payout.booking_transactions_total
        
        # Gastos operacionales de la propiedad (Metidos a mano en la canasta ManyToMany)
        context['property_charges'] = payout.property_charges.all()
        context['property_charges_total'] = payout.property_charges_total
        
        # Gran total neto
        context['net_amount'] = payout.net_amount
        
        return context


class OwnerDashboardListView(LoginRequiredMixin, ListView):
    """
    Vista general para el listado del panel del propietario.
    Muestra el histórico de todos sus pagos recibidos y pendientes.
    """
    model = OwnerPayout
    template_name = 'owner_finances/owner_dashboard.html'
    context_object_name = 'payouts'

    def get_queryset(self):
        # Filtra los payouts para que el propietario logueado solo vea los suyos
        # (Asumiendo que el modelo Property tiene una relación 'owner' apuntando a User)
        return OwnerPayout.objects.filter(
            booking__listing__owner=self.request.user
        ).select_related('booking__listing', 'booking').prefetch_related('property_charges')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        # Totales globales para las tarjetas de KPI del Dashboard del dueño
        context['total_ganado'] = sum(p.net_amount for p in queryset.filter(status='paid'))
        context['total_pendiente'] = sum(p.net_amount for p in queryset.filter(status='pending'))
        
        return context