from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from bookings.models import Booking
from ical_sync.models import IcalBlock 
import calendar
from datetime import date, timedelta

class DashboardIndexView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'dashboard/index.html'
    context_object_name = 'bookings'
    login_url = '/accounts/login/'

    def get_queryset(self):
        return Booking.objects.filter(listing__owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Base temporal
        hoy = date.today()
        modo = self.request.GET.get('modo', 'programadas')
        
        # 2. Captura de parámetros
        raw_month = self.request.GET.get('month', '')
        raw_year = self.request.GET.get('year', '')

        if raw_month.isdigit() and raw_year.isdigit():
            month = int(raw_month)
            year = int(raw_year)
        else:
            month = hoy.month
            year = hoy.year

        # 3. LÓGICA DE MURO (RESTRICCIÓN DINÁMICA)
        # Verificamos si estamos parados exactamente en el mes actual
        es_mes_actual = (year == hoy.year and month == hoy.month)
        
        bloquear_atras = False
        bloquear_adelante = False

        if modo == 'programadas':
            # Si el usuario intenta entrar a un mes pasado por URL, lo devolvemos al hoy
            if year < hoy.year or (year == hoy.year and month < hoy.month):
                year, month = hoy.year, hoy.month
                es_mes_actual = True
            
            # EL MURO: Si está en el mes actual, no puede ir más atrás
            bloquear_atras = es_mes_actual
            # Hacia adelante puede ir todo lo que quiera
            bloquear_adelante = False 
            
        else: # modo == 'realizadas'
            # Si intenta entrar a un mes futuro por URL, lo devolvemos al hoy
            if year > hoy.year or (year == hoy.year and month > hoy.month):
                year, month = hoy.year, hoy.month
                es_mes_actual = True

            # EL MURO: Si está en el mes actual, no puede ir más adelante
            bloquear_adelante = es_mes_actual
            # Hacia atrás (historial) puede ir todo lo que quiera
            bloquear_atras = False

        # 4. Cálculos para los enlaces de los botones
        fecha_actual_view = date(year, month, 1)
        prev_month_date = fecha_actual_view - timedelta(days=1)
        next_month_date = (fecha_actual_view + timedelta(days=32)).replace(day=1)

        # 5. Carga de datos según el contexto
        primer_dia_semana, num_dias = calendar.monthrange(year, month)
        dias_mes = []

        if modo == 'realizadas':
            fuente_datos = Booking.objects.filter(
                listing__owner=self.request.user,
                check_out__gte=date(year, month, 1),
                check_in__lte=date(year, month, num_dias)
            ).select_related('guest')
        else:
            fuente_datos = IcalBlock.objects.filter(
                listing__owner=self.request.user,
                check_out__gte=date(year, month, 1),
                check_in__lte=date(year, month, num_dias)
            )

        # 6. Construcción de la grilla
        for dia in range(1, num_dias + 1):
            fecha_iter = date(year, month, dia)
            registro = fuente_datos.filter(check_in__lte=fecha_iter, check_out__gt=fecha_iter).first()
            
            identificador = None
            if registro:
                if modo == 'realizadas':
                    if registro.guest:
                        # Navegamos: registro (Booking) -> guest (Guest) -> full_name
                        identificador = registro.guest.full_name
                    else:
                        identificador = "Huésped"
                else:
                    # NUEVA LÓGICA: Solo ponemos "Check-in" si es el día de inicio 
                    # Y ADEMÁS es una reserva (is_reservation=True)
                    if registro.check_in == fecha_iter and registro.is_reservation:
                        identificador = "Check-in"
                    # Si es bloqueo (not is_reservation), el identificador se mantiene como None
                    # Así evitamos que aparezca cualquier texto sobre la línea cruzada

            dias_mes.append({
                'dia': dia,
                'fecha': fecha_iter,
                'registro': registro,
                'identificador': identificador,
                'es_hoy': fecha_iter == hoy,
                'es_pasado': (fecha_iter < hoy and modo == 'programadas'),
            })

        # 7. Contexto para el template
        context.update({
            'hoy': hoy,
            'dias_mes': dias_mes,
            'espacios_inicio': range(primer_dia_semana),
            'nombre_mes': fecha_actual_view.strftime('%B %Y').capitalize(),
            'prev_month': prev_month_date,
            'next_month': next_month_date,
            'modo': modo,
            'bloquear_atras': bloquear_atras,
            'bloquear_adelante': bloquear_adelante,
        })
        return context