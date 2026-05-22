from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from datetime import date, timedelta
import calendar
from .models import Booking

class DashboardIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html' # Ajusta a la ruta de tu carpeta de templates

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Obtener Mes y Año (de la URL o actual)
        hoy = date.today()
        month = int(self.request.GET.get('month', hoy.month))
        year = int(self.request.GET.get('year', hoy.year))
        
        inicio_mes = date(year, month, 1)
        _, num_dias = calendar.monthrange(year, month)
        fin_mes = date(year, month, num_dias)

        # 2. Traer Reservas del usuario que toquen este mes
        reservas = Booking.objects.filter(
            listing__owner=self.request.user,
            check_out__gt=inicio_mes,
            check_in__lte=fin_mes
        ).select_related('listing', 'guest')

        ingresos_netos_mes = 0
        noches_ocupadas_mes = 0

        # 3. Lógica de Prorrateo
        for b in reservas:
            # Calcular días exactos dentro de este mes
            check_in_real = max(b.check_in, inicio_mes)
            check_out_real = min(b.check_out, fin_mes + timedelta(days=1))
            noches_en_mes = (check_out_real - check_in_real).days
            
            if noches_en_mes > 0:
                noches_totales = (b.check_out - b.check_in).days
                # Usamos tu campo 'owner_payout' del modelo
                pago_diario = b.owner_payout / noches_totales if noches_totales > 0 else 0
                
                ingresos_netos_mes += (pago_diario * noches_en_mes)
                noches_ocupadas_mes += noches_en_mes

        # 4. Cálculo de KPIs para los botones de arriba
        ocupacion = (noches_ocupadas_mes / num_dias * 100) if num_dias > 0 else 0
        promedio_dia = (ingresos_netos_mes / noches_ocupadas_mes) if noches_ocupadas_mes > 0 else 0

        context.update({
            'kpi_ingresos': ingresos_netos_mes,
            'kpi_ocupacion': ocupacion,
            'kpi_promedio_dia': promedio_dia,
            'kpi_calificacion': 5.0, # Por ahora manual
            'month': month,
            'year': year,
            'nombre_mes': inicio_mes.strftime('%B'),
        })
        return context