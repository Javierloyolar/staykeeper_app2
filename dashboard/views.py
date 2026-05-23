from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from bookings.models import Booking
from ical_sync.models import IcalBlock 
import calendar
from datetime import date, timedelta
from owner_finances.models import OwnerFinancialTransaction

# --- HELPER DE MÉTRICAS ---
def obtener_metricas_hub(user, year, month):
    inicio_mes = date(year, month, 1)
    _, num_dias = calendar.monthrange(year, month)
    fin_mes = date(year, month, num_dias)

    reservas = Booking.objects.filter(
        listing__owner=user,
        check_out__gt=inicio_mes,
        check_in__lte=fin_mes
    ).select_related('listing')

    ingresos_netos = 0
    noches_ocupadas_mes = 0

    for b in reservas:
        c_in = max(b.check_in, inicio_mes)
        c_out = min(b.check_out, fin_mes + timedelta(days=1))
        noches_en_mes = (c_out - c_in).days
        
        if noches_en_mes > 0:
            total_noches_reserva = (b.check_out - b.check_in).days
            pago_diario = b.owner_payout / total_noches_reserva if total_noches_reserva > 0 else 0
            ingresos_netos += (pago_diario * noches_en_mes)
            noches_ocupadas_mes += noches_en_mes

    return {
        'ingresos': ingresos_netos,
        'ocupacion': (noches_ocupadas_mes / num_dias * 100) if num_dias > 0 else 0,
        'media_dia': (ingresos_netos / noches_ocupadas_mes) if noches_ocupadas_mes > 0 else 0,
    }

# --- VISTA PRINCIPAL ---
class DashboardIndexView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'dashboard/index.html'
    context_object_name = 'bookings'
    login_url = '/accounts/login/'

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['dashboard/partials/dashboard_principal_owner.html']
        return ['dashboard/index.html']

    def get_queryset(self):
        return Booking.objects.filter(listing__owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = date.today()
        modo = self.request.GET.get('modo', 'programadas')
        
        raw_month = self.request.GET.get('month', '')
        raw_year = self.request.GET.get('year', '')

        if raw_month.isdigit() and raw_year.isdigit():
            month, year = int(raw_month), int(raw_year)
        else:
            month, year = hoy.month, hoy.year

        # Lógica de Muro
        es_mes_actual = (year == hoy.year and month == hoy.month)
        bloquear_atras = (modo == 'programadas' and es_mes_actual)
        bloquear_adelante = (modo == 'realizadas' and es_mes_actual)

        # Si el usuario "salta" el muro por URL, lo devolvemos
        if modo == 'programadas' and (year < hoy.year or (year == hoy.year and month < hoy.month)):
            month, year, es_mes_actual, bloquear_atras = hoy.month, hoy.year, True, True
        elif modo == 'realizadas' and (year > hoy.year or (year == hoy.year and month > hoy.month)):
            month, year, es_mes_actual, bloquear_adelante = hoy.month, hoy.year, True, True

        # Fechas navegación
        fecha_actual_view = date(year, month, 1)
        prev_month_date = fecha_actual_view - timedelta(days=1)
        next_month_date = (fecha_actual_view + timedelta(days=32)).replace(day=1)

        # Carga de datos
        primer_dia_semana, num_dias = calendar.monthrange(year, month)
        if modo == 'realizadas':
            fuente_datos = Booking.objects.filter(
                listing__owner=self.request.user,
                check_out__gt=date(year, month, 1),
                check_in__lte=date(year, month, num_dias)
            ).select_related('guest','payout')

            # Prorrateamos los montos para cada reserva individual dentro de fuente_datos
            inicio_mes = date(year, month, 1)
            fin_mes = date(year, month, num_dias)
            for b in fuente_datos:
                c_in = max(b.check_in, inicio_mes)
                c_out = min(b.check_out, fin_mes + timedelta(days=1))
                b.noches_en_mes = (c_out - c_in).days
                
                total_noches_reserva = (b.check_out - b.check_in).days
                pago_diario = b.owner_payout / total_noches_reserva if total_noches_reserva > 0 else 0
                b.pago_prorrateado = int(pago_diario * b.noches_en_mes)
                # Extras
                txs = b.owner_transactions.all()
                b.extras_total = sum(t.owner_share for t in txs) if txs.exists() else None

                # Total fila
                b.total_fila = b.pago_prorrateado + (b.extras_total or 0)

                # Estado de pago
                try:
                    b.estado_pago = b.payout.status
                    b.fecha_pago = b.payout.paid_date
                except:
                    b.estado_pago = 'pending'
                    b.fecha_pago = None

        else:
            fuente_datos = IcalBlock.objects.filter(
                listing__owner=self.request.user,
                check_out__gt=date(year, month, 1),
                check_in__lte=date(year, month, num_dias)
            )

        # Construcción de la grilla
        dias_mes = []
        for dia in range(1, num_dias + 1):
            fecha_iter = date(year, month, dia)
            registro = fuente_datos.filter(check_in__lte=fecha_iter, check_out__gt=fecha_iter).first()
            
            identificador = None
            if registro:
                if modo == 'realizadas':
                    identificador = registro.guest.full_name if registro.guest else "Huésped"
                elif registro.check_in == fecha_iter and registro.is_reservation:
                    identificador = "Check-in"

            dias_mes.append({
                'dia': dia,
                'fecha': fecha_iter,
                'registro': registro,
                'identificador': identificador,
                'es_hoy': fecha_iter == hoy,
                'es_pasado': (fecha_iter < hoy and modo == 'programadas'),
            })
        
        # Corrección del parámetro stats
        stats = obtener_metricas_hub(self.request.user, year, month)

        context.update({
            'month': month,
            'year': year,
            'hoy': hoy,
            'dias_mes': dias_mes,
            'fuente_datos': fuente_datos,
            'espacios_inicio': range(primer_dia_semana),
            'nombre_mes': fecha_actual_view.strftime('%B %Y').capitalize(),
            'prev_month': prev_month_date,
            'next_month': next_month_date,
            'modo': modo,
            'bloquear_atras': bloquear_atras,
            'bloquear_adelante': bloquear_adelante,
            'kpi_ingresos': stats['ingresos'],
            'kpi_ocupacion': stats['ocupacion'],
            'kpi_calificacion': 5.0,
        })
        return context

# --- NO OLVIDES AGREGAR ESTA VISTA PARA HTMX ---
class DetalleFinancieroView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'dashboard/partials/detalle_financiero.html'
    context_object_name = 'reservas'

    def get_queryset(self):
        month = int(self.request.GET.get('month', date.today().month))
        year = int(self.request.GET.get('year', date.today().year))
        inicio = date(year, month, 1)
            # Obtenemos el número de días del mes (el segundo valor de la tupla)
        _, num_dias = calendar.monthrange(year, month)
        fin = date(year, month, num_dias)
        
        queryset = Booking.objects.filter(
            listing__owner=self.request.user,
            check_out__gt=inicio,
            check_in__lte=fin
        ).select_related('listing', 'guest', 'payout')
        

        for b in queryset:
            # Tu lógica de prorrateo (que está perfecta)
            c_in, c_out = max(b.check_in, inicio), min(b.check_out, fin + timedelta(days=1))
            noches_mes = (c_out - c_in).days
            total_noches = (b.check_out - b.check_in).days
            pago_diario = b.owner_payout / total_noches if total_noches > 0 else 0
            b.noches_en_mes = noches_mes
            b.pago_prorrateado = int(pago_diario * noches_mes)
            
            # Extras: suma owner_share de todas las transacciones de esta reserva
            txs = b.owner_transactions.all()
            b.extras_total = sum(t.owner_share for t in txs) if txs.exists() else None
            
            # Total fila
            b.total_fila = b.pago_prorrateado + (b.extras_total or 0)

            # Estado de pago
            try:
                b.estado_pago = b.payout.status  # 'pending' o 'paid'
                b.fecha_pago = b.payout.paid_date
            except:
                b.estado_pago = 'pending'
                b.fecha_pago = None
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = int(self.request.GET.get('month', date.today().month))
        year = int(self.request.GET.get('year', date.today().year))
        context['month'] = month
        context['year'] = year
         # Gastos de propiedad acordados para este mes (sin reserva, incluidos en algún payout)
        gastos_propiedad = OwnerFinancialTransaction.objects.filter(
            listing__owner=self.request.user,
            booking__isnull=True,
            included_in_payouts__booking__listing__owner=self.request.user,
            included_in_payouts__booking__check_out__year=year,
            included_in_payouts__booking__check_out__month=month,
        ).distinct()

        context['gastos_propiedad'] = gastos_propiedad
        context['gastos_propiedad_total'] = sum(t.owner_share for t in gastos_propiedad)
        reservas = context['reservas']
        context['total_mes'] = sum(b.total_fila for b in reservas) - context['gastos_propiedad_total']
        return context
        