from django.contrib import admin
from .models import Guest

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    # Mostramos el nombre y email en la lista principal
    list_display = ('id', 'full_name', 'email')
    # Añadimos un buscador por nombre y correo
    search_fields = ('full_name', 'email')