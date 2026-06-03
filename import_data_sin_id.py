import os
import sys
import django
import csv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bookings.models import Booking
from guests.models import Guest

def cargar_datos():

    # --- GUESTS ---
    print("Cargando Huéspedes...")
    with open('guests_2.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            nombre = row['full_name'].strip()
            if not nombre:
                continue
            guest_existe = Guest.objects.filter(full_name=nombre).first()
            if not guest_existe:
                Guest.objects.create(
                    full_name=nombre,
                    email=row.get('email', '')
                )
                print(f"✓ Huésped {nombre} creado.")
            else:
                print(f"— {nombre} ya existe, saltando...")

    # --- BOOKINGS ---
    print("\nCargando Reservas...")
    creadas = 0
    saltadas = 0
    with open('bookings_2.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            guest = Guest.objects.filter(
                full_name=row['guest_name'].strip()
            ).first()
            if not guest:
                print(f"⚠️  Huésped '{row['guest_name']}' no encontrado, saltando {row['reservation_code']}...")
                saltadas += 1
                continue

            obj, created = Booking.objects.get_or_create(
                reservation_code=row['reservation_code'].strip(),
                defaults={
                    'listing_id':    int(row['listing_id']),
                    'guest':         guest,
                    'check_in':      row['check_in'].strip(),
                    'check_out':     row['check_out'].strip(),
                    'net_revenue':   int(row['net_revenue']),
                    'cleaning_fee':  int(row['cleaning_fee']),
                    'pet_fee':       int(row['pet_fee']),
                    'platform':      row['platform'].strip(),
                }
            )
            if created:
                print(f"✓ {row['reservation_code']} creada.")
                creadas += 1
            else:
                print(f"— {row['reservation_code']} ya existía.")
                saltadas += 1

    print(f"\n─── Resumen ───")
    print(f"✓ Creadas:  {creadas}")
    print(f"⚠️  Saltadas: {saltadas}")

if __name__ == "__main__":
    cargar_datos()