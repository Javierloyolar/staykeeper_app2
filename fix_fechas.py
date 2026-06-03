import os
import sys
import django
import csv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bookings.models import Booking

def corregir_fechas():
    print("Corrigiendo fechas...")
    actualizadas = 0
    no_encontradas = 0
    
    with open('fix_fechas.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                booking = Booking.objects.get(reservation_code=row['reservation_code'].strip())
                booking.check_in = row['check_in'].strip()
                booking.check_out = row['check_out'].strip()
                booking.save()
                print(f"✓ {row['reservation_code']} actualizada")
                actualizadas += 1
            except Booking.DoesNotExist:
                print(f"⚠️  {row['reservation_code']} no encontrada")
                no_encontradas += 1

    print(f"\n─── Resumen ───")
    print(f"✓ Actualizadas: {actualizadas}")
    print(f"⚠️  No encontradas: {no_encontradas}")

if __name__ == "__main__":
    corregir_fechas()