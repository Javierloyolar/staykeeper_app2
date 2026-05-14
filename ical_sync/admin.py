from django.contrib import admin
from .models import IcalBlock

@admin.register(IcalBlock)
class IcalBlockAdmin(admin.ModelAdmin):
    # Solo campos que existen en tu modelo simplificado
    list_display = ('listing', 'check_in', 'check_out', 'is_reservation')
    list_filter = ('is_reservation', 'listing')
    # Eliminamos 'source' y 'last_updated' de aquí porque ya no existen