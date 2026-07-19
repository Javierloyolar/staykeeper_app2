import csv
import logging
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from guests.models import Guest
from properties.models import Property
from bookings.models import Booking

REQUIRED_FIELDS = [
    'Código de confirmación',
    'Fecha de inicio',
    'Fecha de finalización',
    'Huésped',
    'Anuncio',
    'Monto',
]

CAMPOS_MONTO = ['Monto', 'Tarifa de limpieza', 'Tarifa por mascotas']
CAMPOS_IDENTIDAD = ['Fecha de inicio', 'Fecha de finalización', 'Huésped', 'Anuncio']


def parse_monto(valor):
    valor = (valor or '').strip()
    return Decimal(valor) if valor else Decimal('0')


class Command(BaseCommand):
    help = "Importa reservas directamente desde el CSV crudo exportado de Airbnb"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument('--dry-run', action='store_true',
                             help='Simula la importación sin escribir nada en la base de datos')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dry_run = options['dry_run']
        creados = existentes = saltados_listing = saltados_incompletos = saltados_error = 0

        log_path = Path(csv_path).with_name('errores_import.log')
        logger = logging.getLogger('import_airbnb')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        fh = logging.FileHandler(log_path, mode='a', encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(fh)
        modo = "DRY-RUN" if dry_run else "REAL"
        logger.info(f"=== Iniciando importación de {csv_path} — modo: {modo} ===")
        if dry_run:
            self.stdout.write(self.style.WARNING("=== MODO DRY-RUN: no se escribe nada en la BD ===\n"))

        try:
            f = open(csv_path, encoding='utf-8-sig')
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"❌ No se encontró el archivo: {csv_path}"))
            logger.error(f"Archivo no encontrado: {csv_path}")
            return

        reader = csv.DictReader(f)
        columnas_faltantes = [c for c in REQUIRED_FIELDS if c not in (reader.fieldnames or [])]
        if columnas_faltantes:
            msg = f"El CSV no tiene las columnas esperadas: {columnas_faltantes}."
            self.stderr.write(self.style.ERROR(f"❌ {msg}"))
            logger.error(msg)
            f.close()
            return

        # --- PASO 1: un solo recorrido, agrupando por reservation_code ---
        reservas = {}

        for row in reader:
            faltantes = [c for c in REQUIRED_FIELDS if not (row.get(c) or '').strip()]
            if faltantes:
                saltados_incompletos += 1
                continue

            codigo = row['Código de confirmación'].strip()

            if codigo not in reservas:
                # Primera vez que vemos este código: guardamos la fila completa,
                # convirtiendo SOLO los campos de monto a Decimal (sin sumar nada aún).
                fila = row.copy()
                for campo in CAMPOS_MONTO:
                    fila[campo] = parse_monto(row[campo])
                fila['_partes'] = 1
                reservas[codigo] = fila
            else:
                existente = reservas[codigo]
                # Validación de identidad: solo fusionamos si es realmente la misma
                # reserva partida en cuotas, no un choque de código por error de Airbnb.
                mismatch = next(
                    (c for c in CAMPOS_IDENTIDAD if existente[c].strip() != row[c].strip()),
                    None
                )
                if mismatch:
                    msg = (f"Reserva {codigo} aparece repetida pero el campo '{mismatch}' no coincide "
                           f"('{existente[mismatch]}' vs '{row[mismatch]}') — no se fusiona, revisar a mano")
                    self.stdout.write(self.style.ERROR(f"❌ {msg}"))
                    logger.error(msg)
                    saltados_error += 1
                    continue

                # Todo coincide -> sí es partición de pago, se suma
                for campo in CAMPOS_MONTO:
                    existente[campo] += parse_monto(row[campo])
                existente['_partes'] += 1

        f.close()

        # --- PASO 2: un Booking por cada reserva ya agrupada ---
        for codigo, fila in reservas.items():
            try:
                if fila['_partes'] > 1:
                    msg = (f"Reserva {codigo} venía en {fila['_partes']} filas (pago en cuotas/ajuste), "
                           f"montos sumados: Monto={fila['Monto']}, Limpieza={fila['Tarifa de limpieza']}, "
                           f"Mascotas={fila['Tarifa por mascotas']}")
                    self.stdout.write(self.style.WARNING(f"ℹ️  {msg}"))
                    logger.info(msg)

                listing_name = fila['Anuncio'].strip()
                property_obj = Property.objects.filter(airbnb_listing_name=listing_name).first()
                if not property_obj:
                    msg = f"Listing '{listing_name}' no encontrado, saltando reserva {codigo}"
                    self.stdout.write(self.style.WARNING(f"⚠️  {msg}"))
                    logger.info(msg)
                    saltados_listing += 1
                    continue

                guest_name = fila['Huésped'].strip()
                guests_matching = Guest.objects.filter(full_name=guest_name)
                if guests_matching.count() > 1:
                    msg = f"Hay {guests_matching.count()} huéspedes con nombre '{guest_name}', usando el primero"
                    self.stdout.write(self.style.WARNING(f"⚠️  {msg}"))
                    logger.info(msg)
                guest_existente = guests_matching.first()

                check_in = datetime.strptime(fila['Fecha de inicio'].strip(), '%m/%d/%Y').date()
                check_out = datetime.strptime(fila['Fecha de finalización'].strip(), '%m/%d/%Y').date()

                net_revenue = int(fila['Monto'])
                cleaning_fee = int(fila['Tarifa de limpieza'])
                pet_fee = int(fila['Tarifa por mascotas'])

                ya_existe = Booking.objects.filter(reservation_code=codigo).exists()

                if dry_run:
                    if ya_existe:
                        self.stdout.write(f"[DRY-RUN] — Reserva {codigo} ya existía, se saltaría")
                        existentes += 1
                    else:
                        estado = "existente" if guest_existente else "NUEVO"
                        self.stdout.write(self.style.SUCCESS(
                            f"[DRY-RUN] ✓ Se crearía {codigo} ({check_in.isoformat()} → {check_out.isoformat()}, "
                            f"huésped: {guest_name} [{estado}], listing: {property_obj.name}, "
                            f"net_revenue={net_revenue}, cleaning_fee={cleaning_fee}, pet_fee={pet_fee})"
                        ))
                        creados += 1
                    continue

                guest = guest_existente or Guest.objects.create(full_name=guest_name)

                obj, created = Booking.objects.get_or_create(
                    reservation_code=codigo,
                    defaults={
                        'listing_id': property_obj.id,
                        'guest': guest,
                        'check_in': check_in,
                        'check_out': check_out,
                        'net_revenue': net_revenue,
                        'cleaning_fee': cleaning_fee,
                        'pet_fee': pet_fee,
                        'platform': 'Airbnb',
                    }
                )

                if created:
                    msg = f"Reserva {codigo} creada (net_revenue={net_revenue})"
                    self.stdout.write(self.style.SUCCESS(f"✓ {msg}"))
                    logger.info(msg)
                    creados += 1
                else:
                    self.stdout.write(f"— Reserva {codigo} ya existía, se salta")
                    existentes += 1

            except Exception as e:
                msg = f"Error en reserva '{codigo}': {e} — se salta"
                self.stdout.write(self.style.WARNING(f"⚠️  {msg}"))
                logger.warning(msg)
                saltados_error += 1
                continue

        resumen = (
            f"Resumen ({modo}): {creados} creadas | {existentes} ya existían | "
            f"{saltados_listing} sin listing | {saltados_incompletos} no eran reservas | "
            f"{saltados_error} con error/mismatch"
        )
        self.stdout.write(self.style.SUCCESS(f"\n{resumen}"))
        logger.info(resumen)
        logger.info(f"Log guardado en: {log_path}\n")