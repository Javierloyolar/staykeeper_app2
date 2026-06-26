from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from bookings.models import Booking
from ical_sync.models import IcalBlock 
import calendar
from datetime import date, timedelta
from owner_finances.models import OwnerFinancialTransaction
import json

MESES_ES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
            'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

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

        raw_month = self.request.GET.get('month', '')
        raw_year = self.request.GET.get('year', '')

        if raw_month.isdigit() and raw_year.isdigit():
            month, year = int(raw_month), int(raw_year)
        else:
            month, year = hoy.month, hoy.year

        # Fechas navegación — sin restricciones de modo
        fecha_actual_view = date(year, month, 1)
        prev_month_date = fecha_actual_view - timedelta(days=1)
        next_month_date = (fecha_actual_view + timedelta(days=32)).replace(day=1)
        # Para que el Dashboard solo muestre hasta un mes hacia adelante
        mes_max = (hoy.replace(day=1) + timedelta(days=32)).replace(day=1)
        es_mes_maximo = next_month_date > mes_max

        # --- Calendario fusionado (Booking + IcalBlock) ---
        primer_dia_semana, num_dias = calendar.monthrange(year, month)
        total_celdas = primer_dia_semana + num_dias
        celdas_faltantes = 42 - total_celdas if total_celdas < 42 else 0
        inicio_mes = date(year, month, 1)
        fin_mes = date(year, month, num_dias)

        reservas = Booking.objects.filter(
            listing__owner=self.request.user,
            check_out__gt=inicio_mes,
            check_in__lte=fin_mes
        )

        
        # IcalBlock completo — reservas y bloqueos
        ical_eventos = IcalBlock.objects.filter(
            listing__owner=self.request.user,
            check_out__gt=inicio_mes,
            check_in__lte=fin_mes,
        )

        dias_mes = []
        for dia in range(1, num_dias + 1):
            fecha_iter = date(year, month, dia)

            # Prioridad 1: Booking real
            reserva = reservas.filter(
                check_in__lte=fecha_iter,
                check_out__gt=fecha_iter
            ).first()

            es_reserva = False
            es_bloqueo = False
            es_inicio_reserva = False
            es_fin_reserva = False
            es_dia_unico = False
            registro = None

            if reserva:
                es_reserva = True
                registro = reserva
            else:
                # Prioridad 2: IcalBlock
                ical = ical_eventos.filter(
                    check_in__lte=fecha_iter,
                    check_out__gt=fecha_iter
                ).first()
                if ical:
                    if ical.is_reservation:
                        es_reserva = True
                        registro = ical
                    else:
                        es_bloqueo = True
                        registro = ical

            if registro and es_reserva:
                es_inicio_reserva = fecha_iter == registro.check_in
                es_fin_reserva = fecha_iter == (registro.check_out - timedelta(days=1))
                es_dia_unico = es_inicio_reserva and es_fin_reserva

            dias_mes.append({
                'dia': dia,
                'es_reserva': es_reserva,
                'es_bloqueo': es_bloqueo,
                'es_inicio_reserva': es_inicio_reserva,
                'es_fin_reserva': es_fin_reserva,
                'es_dia_unico': es_dia_unico,
                'es_hoy': fecha_iter == hoy,
            })
        
        # --- Stats del mes para el dashboard ---
        noches_reservadas_dash = sum(1 for d in dias_mes if d['es_reserva'])
        noches_bloqueadas_dash = sum(1 for d in dias_mes if d['es_bloqueo'])
        noches_sin_reserva_dash = num_dias - noches_reservadas_dash - noches_bloqueadas_dash

        # --- KPIs ---
        stats = obtener_metricas_hub(self.request.user, year, month)

        # --- Próximos movimientos (15 días hacia adelante) ---
        limite = hoy + timedelta(days=15)

        proximos_checkins = list(Booking.objects.filter(
            listing__owner=self.request.user,
            check_in__gte=hoy,
            check_in__lte=limite,
        ).order_by('check_in')[:4])

        proximos_checkouts = list(Booking.objects.filter(
            listing__owner=self.request.user,
            check_out__gte=hoy,
            check_out__lte=limite,
        ).order_by('check_out')[:4])

        # iCal sin Booking correspondiente — checkins
        proximos_ical_checkin = []
        for b in IcalBlock.objects.filter(
            listing__owner=self.request.user,
            check_in__gte=hoy,
            check_in__lte=limite,
            is_reservation=True,
        ).order_by('check_in')[:8]:
            ya_tiene_booking = Booking.objects.filter(
                listing__owner=self.request.user,
                check_in=b.check_in,
            ).exists()
            if not ya_tiene_booking:
                proximos_ical_checkin.append(b)
            if len(proximos_ical_checkin) >= 4:
                break

        # iCal sin Booking correspondiente — checkouts
        proximos_ical_checkout = []
        for b in IcalBlock.objects.filter(
            listing__owner=self.request.user,
            check_out__gte=hoy,
            check_out__lte=limite,
            is_reservation=True,
        ).order_by('check_out')[:8]:
            ya_tiene_booking = Booking.objects.filter(
                listing__owner=self.request.user,
                check_out=b.check_out,
            ).exists()
            if not ya_tiene_booking:
                proximos_ical_checkout.append(b)
            if len(proximos_ical_checkout) >= 4:
                break

        proximos_movimientos = sorted(
            [{'tipo': 'checkin', 'fecha': b.check_in, 'booking': b, 'dias': (b.check_in - hoy).days} for b in proximos_checkins] +
            [{'tipo': 'checkout', 'fecha': b.check_out, 'booking': b, 'dias': (b.check_out - hoy).days} for b in proximos_checkouts] +
            [{'tipo': 'checkin', 'fecha': b.check_in, 'booking': b, 'dias': (b.check_in - hoy).days} for b in proximos_ical_checkin] +
            [{'tipo': 'checkout', 'fecha': b.check_out, 'booking': b, 'dias': (b.check_out - hoy).days} for b in proximos_ical_checkout],
            key=lambda x: x['fecha']
        )[:4]

        # --- Ventana móvil de ingresos ---
        ingresos_ventana = []
        for i in range(-3, 3):
            m = month + i
            y = year
            while m < 1:
                m += 12
                y -= 1
            while m > 12:
                m -= 12
                y += 1
            stats_ventana = obtener_metricas_hub(self.request.user, y, m)
            ingresos_ventana.append({
                'label': f"{MESES_ES[m-1][:3]} {y}",
                'ingresos': round(stats_ventana['ingresos']),
                'es_actual': (m == month and y == year),
            })

        context.update({
            'month': month,
            'year': year,
            'hoy': hoy,
            'dias_mes': dias_mes,
            'espacios_inicio': range(primer_dia_semana),
            'celdas_faltantes': range(celdas_faltantes),
            'nombre_mes': f"{MESES_ES[month-1]} {year}",
            'prev_month': prev_month_date,
            'next_month': next_month_date,
            'es_mes_maximo': es_mes_maximo,
            'kpi_ingresos': stats['ingresos'],
            'kpi_ocupacion': stats['ocupacion'],
            'kpi_calificacion': 5.0,
            'proximos_movimientos': proximos_movimientos,
            'ingresos_ventana_json': json.dumps([d['ingresos'] for d in ingresos_ventana]),
            'ingresos_ventana_labels_json': json.dumps([d['label'] for d in ingresos_ventana]),
            'ingresos_ventana_actual_idx': next(i for i, d in enumerate(ingresos_ventana) if d['es_actual']),
            'noches_reservadas_dash': noches_reservadas_dash,
            'noches_bloqueadas_dash': noches_bloqueadas_dash,
            'noches_sin_reserva_dash': noches_sin_reserva_dash,
        })
        return context




class KpiIngresosView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'dashboard/partials/kpi_ingresos.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        return Booking.objects.filter(listing__owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = date.today()

        # Todos los años disponibles — últimos 4
        todos_los_años = {}
        for y in range(hoy.year - 3, hoy.year + 1):
            datos = [
                round(obtener_metricas_hub(self.request.user, y, m)['ingresos'])
                for m in range(1, 13)
            ]
            todos_los_años[y] = datos

        años_con_datos = [y for y, d in todos_los_años.items() if any(v > 0 for v in d)]
        hay_comparativo = len(años_con_datos) >= 2

        context.update({
            'año_actual': hoy.year,
            'todos_los_años_json': json.dumps(todos_los_años),
            'años_con_datos': años_con_datos,
            'hay_comparativo': hay_comparativo,
            'comparativo_json': json.dumps({
                str(y): todos_los_años[y] for y in años_con_datos
            }),
        })
        return context

class KpiOcupacionView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'dashboard/partials/kpi_ocupacion.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        return Booking.objects.filter(listing__owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = date.today()

        # Mes anterior como default
        if hoy.month > 1:
            mes_default = hoy.month - 1
            anio_default_mes = hoy.year
        else:
            mes_default = 12
            anio_default_mes = hoy.year - 1

        # Últimos 12 meses hacia atrás desde el mes anterior
        todos_los_meses = {}
        for i in range(12):
            # Calcular mes y año i meses atrás desde mes_default
            m = mes_default - i
            y = anio_default_mes
            while m < 1:
                m += 12
                y -= 1

            inicio_mes = date(y, m, 1)
            _, num_dias = calendar.monthrange(y, m)
            fin_mes = date(y, m, num_dias)

            reservas = Booking.objects.filter(
                listing__owner=self.request.user,
                check_out__gt=inicio_mes,
                check_in__lte=fin_mes
            )

            bloqueos = IcalBlock.objects.filter(
                listing__owner=self.request.user,
                check_out__gt=inicio_mes,
                check_in__lte=fin_mes,
                is_reservation=False
            )

            noches_reservadas = 0
            noches_fds_reservadas = 0
            noches_semana_reservadas = 0
            noches_fds_total = 0
            noches_semana_total = 0

            for dia in range(1, num_dias + 1):
                fecha = date(y, m, dia)
                es_fds = fecha.weekday() in (4, 5)
                if es_fds:
                    noches_fds_total += 1
                else:
                    noches_semana_total += 1

                if reservas.filter(check_in__lte=fecha, check_out__gt=fecha).exists():
                    noches_reservadas += 1
                    if es_fds:
                        noches_fds_reservadas += 1
                    else:
                        noches_semana_reservadas += 1

            noches_bloqueadas = sum(
                1 for dia in range(1, num_dias + 1)
                if bloqueos.filter(
                    check_in__lte=date(y, m, dia),
                    check_out__gt=date(y, m, dia)
                ).exists()
            )

            # Usamos una clave compuesta año-mes para el JS
            clave = f"{y}-{m:02d}"
            todos_los_meses[clave] = {
                'anio': y,
                'mes': m,
                'num_dias': num_dias,
                'noches_reservadas': noches_reservadas,
                'noches_bloqueadas': noches_bloqueadas,
                'noches_disponibles': num_dias - noches_reservadas - noches_bloqueadas,
                'ocupacion': round(noches_reservadas / num_dias * 100, 1),
                'ocupacion_fds': round(noches_fds_reservadas / noches_fds_total * 100, 1) if noches_fds_total > 0 else 0,
                'ocupacion_semana': round(noches_semana_reservadas / noches_semana_total * 100, 1) if noches_semana_total > 0 else 0,
            }

        # ── Card 2: comparativo entre años ──
        todos_los_anios = {}
        for y in range(hoy.year - 3, hoy.year + 1):
            datos = []
            for m in range(1, 13):
                if y == hoy.year and m >= hoy.month:
                    datos.append(0)
                else:
                    datos.append(
                        round(obtener_metricas_hub(self.request.user, y, m)['ocupacion'], 1)
                    )
            todos_los_anios[y] = datos

        anios_con_datos = [y for y, d in todos_los_anios.items() if any(v > 0 for v in d)]

        context.update({
            'mes_actual': f"{anio_default_mes}-{mes_default:02d}",  # ← clave compuesta
            'anio_actual': anio_default_mes,
            'todos_los_meses_json': json.dumps(todos_los_meses),
            'todos_los_anios_json': json.dumps(todos_los_anios),
            'anios_con_datos': anios_con_datos,
            'comparativo_ocupacion_json': json.dumps({
                str(y): todos_los_anios[y] for y in anios_con_datos
            }),
            'hay_comparativo': len(anios_con_datos) >= 1,
        })
        return context
    

class EstadiaView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'dashboard/estadia.html'
    context_object_name = 'bookings'
    login_url = '/accounts/login/'

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['dashboard/partials/estadia_content.html']
        return ['dashboard/estadia.html']

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

        if modo == 'programadas' and (year < hoy.year or (year == hoy.year and month < hoy.month)):
            month, year, es_mes_actual, bloquear_atras = hoy.month, hoy.year, True, True
        elif modo == 'realizadas' and (year > hoy.year or (year == hoy.year and month > hoy.month)):
            month, year, es_mes_actual, bloquear_adelante = hoy.month, hoy.year, True, True

        fecha_actual_view = date(year, month, 1)
        prev_month_date = fecha_actual_view - timedelta(days=1)
        next_month_date = (fecha_actual_view + timedelta(days=32)).replace(day=1)

        primer_dia_semana, num_dias = calendar.monthrange(year, month)

        if modo == 'realizadas':
            fuente_datos = Booking.objects.filter(
                listing__owner=self.request.user,
                check_out__gt=date(year, month, 1),
                check_in__lte=date(year, month, num_dias)
            ).select_related('guest', 'payout').order_by('check_in')

            inicio_mes = date(year, month, 1)
            fin_mes = date(year, month, num_dias)
            for b in fuente_datos:
                c_in = max(b.check_in, inicio_mes)
                c_out = min(b.check_out, fin_mes + timedelta(days=1))
                b.noches_en_mes = (c_out - c_in).days
                total_noches_reserva = (b.check_out - b.check_in).days
                pago_diario = b.owner_payout / total_noches_reserva if total_noches_reserva > 0 else 0
                b.pago_prorrateado = int(pago_diario * b.noches_en_mes)
                txs = b.owner_transactions.all()
                b.extras_total = sum(t.owner_share for t in txs) if txs.exists() else None
                b.total_fila = b.pago_prorrateado + (b.extras_total or 0)
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

        dias_mes = []
        for dia in range(1, num_dias + 1):
            fecha_iter = date(year, month, dia)
            registro = fuente_datos.filter(check_in__lte=fecha_iter, check_out__gt=fecha_iter).first()
            identificador = None
            es_inicio_reserva = False
            es_fin_reserva = False
            es_medio_reserva = False
            es_dia_unico = False

            if registro:
                es_inicio_reserva = fecha_iter == registro.check_in
                es_fin_reserva = fecha_iter == (registro.check_out - timedelta(days=1))
                es_dia_unico = es_inicio_reserva and es_fin_reserva
                es_medio_reserva = not es_inicio_reserva and not es_fin_reserva

                if modo == 'realizadas':
                    if es_inicio_reserva:
                        identificador = registro.guest.full_name if registro.guest else "Huésped"
                
            dias_mes.append({
                'dia': dia,
                'fecha': fecha_iter,
                'registro': registro,
                'identificador': identificador,
                'es_inicio_reserva': es_inicio_reserva,
                'es_fin_reserva': es_fin_reserva,
                'es_medio_reserva': es_medio_reserva,
                'es_dia_unico': es_dia_unico,
                'es_hoy': fecha_iter == hoy,
                'es_pasado': (fecha_iter < hoy and modo == 'programadas'),                
            })

        stats = obtener_metricas_hub(self.request.user, year, month)

        context.update({
            'month': month,
            'year': year,
            'hoy': hoy,
            'dias_mes': dias_mes,
            'fuente_datos': fuente_datos,
            'espacios_inicio': range(primer_dia_semana),
            'nombre_mes': f"{MESES_ES[month-1]} {year}",
            'prev_month': prev_month_date,
            'next_month': next_month_date,
            'modo': modo,
            'bloquear_atras': bloquear_atras,
            'bloquear_adelante': bloquear_adelante,
            'kpi_ingresos': stats['ingresos'],
        })
        return context