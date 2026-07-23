import os
import uuid
import tempfile

from django.contrib import admin, messages
from django.forms import ModelChoiceField
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
from django.utils import timezone

from .models import Booking, PendingBooking
from .services import importar_airbnb_csv


class ImportAirbnbForm(forms.Form):
    csv_file = forms.FileField(label="Archivo CSV exportado de Airbnb", required=False)
    dry_run = forms.BooleanField(
        label="Solo simular (no escribe nada en la base de datos)",
        required=False,
        initial=True,
    )


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
        'status',
    )
    list_filter = ('listing', 'platform', 'status', 'check_in')
    search_fields = ('reservation_code', 'guest__full_name')
    readonly_fields = ('owner_payout', 'staykeeper_revenue')
    change_list_template = "admin/bookings/booking/change_list.html"

    # Eliminar la acción de borrar
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('Reserva', {
            'fields': ('reservation_code', 'listing', 'guest', 'platform', 'status')
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

            class GuestChoiceField(ModelChoiceField):
                def label_from_instance(self, obj):
                    return obj.full_name

            kwargs['form_class'] = GuestChoiceField
            kwargs['queryset'] = Guest.objects.all().order_by('full_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # --- Botón de importación desde CSV de Airbnb ---

    def get_urls(self):
        custom_urls = [
            path(
                'importar-airbnb/',
                self.admin_site.admin_view(self.importar_airbnb),
                name='bookings_importar_airbnb',
            ),
        ]
        return custom_urls + super().get_urls()

    def importar_airbnb(self, request):
        resultado = None
        form = ImportAirbnbForm()

        if request.method == 'POST':
            accion = request.POST.get('accion')

            # --- Caso 1: se subió un CSV ---
            if accion == 'subir_csv':
                form = ImportAirbnbForm(request.POST, request.FILES)
                if form.is_valid() and form.cleaned_data['csv_file']:
                    uploaded_file = form.cleaned_data['csv_file']
                    dry_run = form.cleaned_data['dry_run']

                    if not uploaded_file.name.lower().endswith('.csv'):
                        messages.error(request, "El archivo debe ser .csv")
                        return render(request, 'admin/bookings/import_airbnb.html', {
                            'form': form, 'resultado': resultado,
                            'pendientes': PendingBooking.objects.filter(status='pending').select_related('listing'),
                            'title': 'Importar reservas desde CSV de Airbnb',
                        })

                    nombre_temporal = f"airbnb_import_{uuid.uuid4().hex}.csv"
                    temp_path = os.path.join(tempfile.gettempdir(), nombre_temporal)

                    try:
                        with open(temp_path, 'wb') as destino:
                            for chunk in uploaded_file.chunks():
                                destino.write(chunk)

                        r = importar_airbnb_csv(temp_path, dry_run=dry_run)

                        if r['archivo_error'] or r['columnas_error']:
                            messages.error(request, r['archivo_error'] or r['columnas_error'])
                        else:
                            resultado = '\n'.join(r['log']) if r['log'] else '(sin novedades)'
                            resultado += (
                                f"\n\nResumen: {r['creados']} creadas | {r['existentes']} ya existían | "
                                f"{r['saltados_listing']} sin listing | {r['saltados_incompletos']} no eran reservas | "
                                f"{r['pendientes_nuevas']} pendientes de revisión | {r['saltados_ya_resueltos']} ya resueltos antes | "
                                f"{r['saltados_error']} con error"
                            )
                            if dry_run:
                                messages.info(request, "Simulación completada. Nada se escribió en la base de datos.")
                            else:
                                messages.success(request, "Importación completada.")

                    except Exception as e:
                        messages.error(request, f"Error al importar: {e}")
                        resultado = str(e)

                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

            # --- Caso 2: se resolvió una fila pendiente ---
            elif accion == 'resolver_pendiente':
                pendiente_id = request.POST.get('pendiente_id')
                decision = request.POST.get('decision')
                p = PendingBooking.objects.get(id=pendiente_id, status='pending')

                if decision == 'activa':
                    if p.overlap_group:
                        ya_confirmada = PendingBooking.objects.filter(
                            overlap_group=p.overlap_group, status='confirmed'
                        ).exclude(id=p.id).exists()
                        if ya_confirmada:
                            messages.error(
                                request,
                                f"No se puede confirmar {p.reservation_code}: ya hay otra reserva "
                                f"activa para las mismas fechas en '{p.listing.name}'."
                            )
                            return redirect(request.path)

                    from guests.models import Guest
                    guest, _ = Guest.objects.get_or_create(full_name=p.guest_name)
                    Booking.objects.get_or_create(
                        reservation_code=p.reservation_code,
                        defaults={
                            'listing_id': p.listing.id, 'guest': guest,
                            'check_in': p.check_in, 'check_out': p.check_out,
                            'net_revenue': p.net_revenue, 'cleaning_fee': p.cleaning_fee,
                            'pet_fee': p.pet_fee, 'platform': 'Airbnb',
                        }
                    )
                    p.status = 'confirmed'
                    messages.success(request, f"{p.reservation_code} confirmada como reserva real.")
                else:
                    p.status = 'cancelled'
                    messages.success(request, f"{p.reservation_code} marcada como cancelada. No se creó ningún Booking.")

                p.resuelto_en = timezone.now()
                p.save()
                return redirect(request.path)

        pendientes = PendingBooking.objects.filter(status='pending').select_related('listing')

        return render(request, 'admin/bookings/import_airbnb.html', {
            'form': form,
            'resultado': resultado,
            'pendientes': pendientes,
            'title': 'Importar reservas desde CSV de Airbnb',
        })