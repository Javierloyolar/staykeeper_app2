from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # Eliminamos 'platform' de aquí para que no de error
    list_display = (
        'reservation_code', 
        'listing', 
        'check_in', 
        'net_revenue', 
        'owner_payout', 
        'staykeeper_revenue'
    )
    list_filter = ('listing', 'platform', 'check_in') # Solo dejamos campos que SI existen
    search_fields = ('reservation_code', 'guest__full_name')
    # Para que no se puedan modificar los cálculos a mano
    readonly_fields = ('owner_payout', 'staykeeper_revenue')