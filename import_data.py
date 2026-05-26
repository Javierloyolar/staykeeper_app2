import os
import sys
import django
import csv

# 1. Asegurar que Python encuentre la carpeta del proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. Configurar el entorno de Django (según tu settings.py es 'config')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings') 
django.setup()

from bookings.models import Booking
from properties.models import Property
from guests.models import Guest

def cargar_datos():
    # --- GUESTS ---
    print("Cargando Huéspedes...")
    with open('guests2.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            Guest.objects.get_or_create(
                full_name=row['full_name'],
                defaults={
                    'email': row['email']
                }
            )

    # --- PROPERTIES ---
    print("Cargando Propiedades...")
    with open('properties.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Usamos el nombre exacto de tu CSV: 'commision_rate'
            Property.objects.get_or_create(
                id=row['id'],
                defaults={
                    'name': row['name'],
                    'airbnb_ical_url': row['airbnb_ical_url'],
                    'owner_id': row['owner_id'],
                    'commission_rate': row['commission_rate'] 
                }
            )

    # --- BOOKINGS ---
    print("Cargando Reservas y calculando StayKeeper metrics...")
    with open('bookings2.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Usamos get_or_create para no chocar con reservas ya cargadas
            obj, created = Booking.objects.get_or_create(
                reservation_code=row['reservation_code'],
                defaults={
                    'listing_id': int(row['listing_id']),
                    'guest_id': int(row['guest_id']),
                    'check_in': row['check_in'],
                    'check_out': row['check_out'],
                    'net_revenue': int(row['net_revenue']),
                    'cleaning_fee': int(row['cleaning_fee']),
                    'pet_fee': int(row['pet_fee']),
                    'platform': row['platform']
                }
            )
            if created:
                print(f"Reserva {row['reservation_code']} creada con éxito.")
            else:
                print(f"Reserva {row['reservation_code']} ya existía, saltando...")

if __name__ == "__main__":
    cargar_datos()