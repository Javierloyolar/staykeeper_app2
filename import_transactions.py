import os
import sys
import django
import csv
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bookings.models import Booking
from owner_finances.models import OwnerFinancialTransaction

def cargar_transacciones():
    print("Cargando Transacciones Financieras...")
    with open('transactions.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Buscar el booking por reservation_code
            try:
                booking = Booking.objects.select_related('listing').get(
                    reservation_code=row['reservation_code']
                )
            except Booking.DoesNotExist:
                print(f"⚠️  Reserva {row['reservation_code']} no encontrada, saltando...")
                continue

            # Crear la transacción — el listing lo sacamos del booking
            OwnerFinancialTransaction.objects.create(
                listing=booking.listing,
                booking=booking,
                amount=int(row['amount']),
                category=row['category'],
                transaction_type=row['transaction_type'],
                owner_impact=row['owner_impact'],
                description=row.get('description', ''),
                transaction_date=row['transaction_date'],
            )
            print(f"✓ Transacción creada: {booking.reservation_code} — {row['category']} ${row['amount']}")

if __name__ == "__main__":
    cargar_transacciones()