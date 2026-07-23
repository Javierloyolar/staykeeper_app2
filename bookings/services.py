import csv
from decimal import Decimal
from datetime import datetime
from collections import defaultdict

from guests.models import Guest
from properties.models import Property
from bookings.models import Booking, PendingBooking

REQUIRED_FIELDS = [
    'Código de confirmación', 'Fecha de inicio', 'Fecha de finalización',
    'Huésped', 'Anuncio', 'Monto',
]
CAMPOS_MONTO = ['Monto', 'Tarifa de limpieza', 'Tarifa por mascotas']
CAMPOS_IDENTIDAD = ['Fecha de inicio', 'Fecha de finalización', 'Huésped', 'Anuncio']

UMBRAL_LIMPIEZA_SOSPECHOSA = 18000  # CLP


def parse_monto(valor):
    valor = (valor or '').strip()
    return Decimal(valor) if valor else Decimal('0')


def _ya_tiene_decision(codigo):
    """
    True si este código ya fue resuelto antes (es un Booking real, o ya
    quedó marcado confirmed/cancelled como PendingBooking) — sin importar
    el motivo (OVERLAP, LOW_CLEANING, o el que sea en el futuro).
    """
    if Booking.objects.filter(reservation_code=codigo).exists():
        return True
    if PendingBooking.objects.filter(
        reservation_code=codigo, status__in=['confirmed', 'cancelled']
    ).exists():
        return True
    return False


def _guardar_pendiente(codigo, fila, property_obj, reason, overlap_group=''):
    """Crea o reutiliza (si ya existía y sigue 'pending') un PendingBooking, sin duplicar."""
    check_in = datetime.strptime(fila['Fecha de inicio'].strip(), '%m/%d/%Y').date()
    check_out = datetime.strptime(fila['Fecha de finalización'].strip(), '%m/%d/%Y').date()

    obj, created = PendingBooking.objects.update_or_create(
        reservation_code=codigo,
        status='pending',
        defaults={
            'listing': property_obj,
            'guest_name': fila['Huésped'].strip(),
            'check_in': check_in,
            'check_out': check_out,
            'net_revenue': int(fila['Monto']),
            'cleaning_fee': int(fila['Tarifa de limpieza']),
            'pet_fee': int(fila['Tarifa por mascotas']),
            'reason': reason,
            'overlap_group': overlap_group,
        }
    )
    return obj, created


def importar_airbnb_csv(csv_path, dry_run=False):
    resultado = {
        'creados': 0, 'existentes': 0, 'saltados_listing': 0,
        'saltados_incompletos': 0, 'saltados_error': 0, 'pendientes_nuevas': 0,
        'saltados_ya_resueltos': 0,
        'log': [], 'archivo_error': None, 'columnas_error': None,
    }

    try:
        f = open(csv_path, encoding='utf-8-sig')
    except FileNotFoundError:
        resultado['archivo_error'] = f"No se encontró el archivo: {csv_path}"
        return resultado

    reader = csv.DictReader(f)
    columnas_faltantes = [c for c in REQUIRED_FIELDS if c not in (reader.fieldnames or [])]
    if columnas_faltantes:
        resultado['columnas_error'] = f"El CSV no tiene las columnas esperadas: {columnas_faltantes}"
        f.close()
        return resultado

    # --- Agrupar por reservation_code (pagos en cuotas) ---
    reservas = {}
    for row in reader:
        faltantes = [c for c in REQUIRED_FIELDS if not (row.get(c) or '').strip()]
        if faltantes:
            resultado['saltados_incompletos'] += 1
            continue
        codigo = row['Código de confirmación'].strip()
        if codigo not in reservas:
            fila = row.copy()
            for campo in CAMPOS_MONTO:
                fila[campo] = parse_monto(row[campo])
            fila['_partes'] = 1
            reservas[codigo] = fila
        else:
            existente = reservas[codigo]
            mismatch = next((c for c in CAMPOS_IDENTIDAD if existente[c].strip() != row[c].strip()), None)
            if mismatch:
                resultado['saltados_error'] += 1
                resultado['log'].append(f"❌ Reserva {codigo}: campo '{mismatch}' no coincide entre filas duplicadas")
                continue
            for campo in CAMPOS_MONTO:
                existente[campo] += parse_monto(row[campo])
            existente['_partes'] += 1
    f.close()

    if dry_run:
        resultado['log'].append("=== DRY-RUN: no se escribe nada, ni Booking ni PendingBooking ===")

    # --- Detectar OVERLAP por listing (pares) ---
    por_listing = defaultdict(list)
    for codigo, datos in reservas.items():
        try:
            ci = datetime.strptime(datos['Fecha de inicio'].strip(), '%m/%d/%Y').date()
            co = datetime.strptime(datos['Fecha de finalización'].strip(), '%m/%d/%Y').date()
        except ValueError:
            continue
        por_listing[datos['Anuncio'].strip()].append((codigo, ci, co))

    codigos_con_overlap = {}  # codigo -> overlap_group

    for listing_name, lista in por_listing.items():
        lista.sort(key=lambda x: x[1])
        for i in range(len(lista)):
            codigo_a, ci_a, co_a = lista[i]
            for j in range(i + 1, len(lista)):
                codigo_b, ci_b, co_b = lista[j]
                if ci_b >= co_a:
                    break  # checkout de A == checkin de B (o después) -> rotación normal, no es solape
                if ci_a < co_b and ci_b < co_a:
                    grupo = '|'.join(sorted([codigo_a, codigo_b]))
                    codigos_con_overlap[codigo_a] = grupo
                    codigos_con_overlap[codigo_b] = grupo

    # --- Procesar cada reserva agrupada ---
    for codigo, fila in reservas.items():
        try:
            listing_name = fila['Anuncio'].strip()
            property_obj = Property.objects.filter(airbnb_listing_name=listing_name).first()
            if not property_obj:
                resultado['saltados_listing'] += 1
                resultado['log'].append(f"⚠️ Listing '{listing_name}' no encontrado, saltando {codigo}")
                continue

            # 0) ¿Este código ya tiene una decisión tomada? -> se omite, sin importar el motivo
            if codigo in codigos_con_overlap or int(fila['Tarifa de limpieza']) < UMBRAL_LIMPIEZA_SOSPECHOSA:
                if _ya_tiene_decision(codigo):
                    resultado['saltados_ya_resueltos'] += 1
                    resultado['log'].append(f"— {codigo} ya tenía una decisión tomada antes, se omite")
                    continue

            # 1) Solape de fechas -> pendiente
            if codigo in codigos_con_overlap:
                if dry_run:
                    resultado['log'].append(f"⛔ [DRY-RUN] {codigo} quedaría PENDIENTE (OVERLAP)")
                else:
                    obj, created = _guardar_pendiente(
                        codigo, fila, property_obj, reason='OVERLAP',
                        overlap_group=codigos_con_overlap[codigo]
                    )
                    resultado['log'].append(
                        f"⛔ {codigo} {'guardada' if created else 'actualizada'} como pendiente (OVERLAP)"
                    )
                resultado['pendientes_nuevas'] += 1
                continue

            # 2) Tarifa de limpieza sospechosamente baja -> pendiente
            cleaning_fee = int(fila['Tarifa de limpieza'])
            if cleaning_fee < UMBRAL_LIMPIEZA_SOSPECHOSA:
                if dry_run:
                    resultado['log'].append(
                        f"⛔ [DRY-RUN] {codigo} quedaría PENDIENTE (LOW_CLEANING, ${cleaning_fee})"
                    )
                else:
                    obj, created = _guardar_pendiente(codigo, fila, property_obj, reason='LOW_CLEANING')
                    resultado['log'].append(
                        f"⛔ {codigo} {'guardada' if created else 'actualizada'} como pendiente "
                        f"(LOW_CLEANING, limpieza=${cleaning_fee})"
                    )
                resultado['pendientes_nuevas'] += 1
                continue

            # 3) Sin anomalías -> flujo normal
            guest_name = fila['Huésped'].strip()
            guest_existente = Guest.objects.filter(full_name=guest_name).first()

            check_in = datetime.strptime(fila['Fecha de inicio'].strip(), '%m/%d/%Y').date()
            check_out = datetime.strptime(fila['Fecha de finalización'].strip(), '%m/%d/%Y').date()
            net_revenue = int(fila['Monto'])
            pet_fee = int(fila['Tarifa por mascotas'])

            if dry_run:
                ya_existe = Booking.objects.filter(reservation_code=codigo).exists()
                if not ya_existe:
                    resultado['creados'] += 1
                    resultado['log'].append(f"[DRY-RUN] ✓ Se crearía {codigo} ({guest_name}, {check_in}→{check_out}, ${net_revenue})")
                else:
                    resultado['existentes'] += 1
                continue

            guest = guest_existente or Guest.objects.create(full_name=guest_name)
            obj, created = Booking.objects.get_or_create(
                reservation_code=codigo,
                defaults={
                    'listing_id': property_obj.id, 'guest': guest,
                    'check_in': check_in, 'check_out': check_out,
                    'net_revenue': net_revenue, 'cleaning_fee': cleaning_fee,
                    'pet_fee': pet_fee, 'platform': 'Airbnb',
                }
            )
            if created:
                resultado['creados'] += 1
                resultado['log'].append(f"✓ Reserva {codigo} creada (net_revenue={net_revenue})")
            else:
                resultado['existentes'] += 1

        except Exception as e:
            resultado['saltados_error'] += 1
            resultado['log'].append(f"⚠️ Error en {codigo}: {e}")
            continue

    return resultado