from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path

from .models import IcalBlock
from .services import sincronizar_todas_las_propiedades


@admin.register(IcalBlock)
class IcalBlockAdmin(admin.ModelAdmin):
    list_display = ('listing', 'check_in', 'check_out', 'is_reservation')
    list_filter = ('is_reservation', 'listing')
    change_list_template = "admin/ical_sync/icalblock/change_list.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_urls(self):
        custom_urls = [
            path('sincronizar/', self.admin_site.admin_view(self.sincronizar), name='ical_sync_sincronizar'),
        ]
        return custom_urls + super().get_urls()

    def sincronizar(self, request):
        if request.method == 'POST':
            r = sincronizar_todas_las_propiedades()
            for linea in r['log']:
                if 'error' in linea.lower() or 'salta' in linea.lower():
                    messages.warning(request, linea)
                else:
                    messages.success(request, linea)
            messages.info(request, f"Resumen: {r['ok']} ok | {r['error']} con error")
        return redirect('admin:ical_sync_icalblock_changelist')