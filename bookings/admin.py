from django.contrib import admin
from .models import Booking
from django.forms import ModelChoiceField

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'reservation_code',
        'listing',
        'get_guest_name',
        'check_in',
        'check_out',
        'net_revenue',
        'owner_payout',
        'staykeeper_revenue',
        'platform',
    )
    list_filter = ('listing', 'platform', 'check_in')
    search_fields = ('reservation_code', 'guest__full_name')
    readonly_fields = ('owner_payout', 'staykeeper_revenue')

    # Eliminar la acción de borrar
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('Reserva', {
            'fields': ('reservation_code', 'listing', 'guest', 'platform')
        }),
        ('Fechas', {
            'fields': ('check_in', 'check_out')
        }),
        ('Montos', {
            'fields': ('net_revenue', 'cleaning_fee', 'pet_fee', 'owner_payout', 'staykeeper_revenue'),
            'description': 'owner_payout y staykeeper_revenue se calculan automáticamente.'
        }),
    )

    def get_guest_name(self, obj):
        return obj.guest.full_name if obj.guest else '—'
    get_guest_name.short_description = 'Huésped'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'guest':
            from guests.models import Guest
            from django.forms import ModelChoiceField

            class GuestChoiceField(ModelChoiceField):
                def label_from_instance(self, obj):
                    return obj.full_name

            kwargs['form_class'] = GuestChoiceField
            kwargs['queryset'] = Guest.objects.all().order_by('full_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)