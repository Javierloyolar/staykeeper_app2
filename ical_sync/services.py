import requests
from datetime import datetime
from icalendar import Calendar

from properties.models import Property
from .models import IcalBlock


def sincronizar_ical_propiedad(property_obj):
    """Sincroniza el iCal de UNA propiedad. Devuelve (ok: bool, mensaje: str)."""
    if not property_obj.airbnb_ical_url:
        return False, f"{property_obj.name}: sin URL de iCal configurada, se salta"

    try:
        response = requests.get(property_obj.airbnb_ical_url, timeout=10)
        response.raise_for_status()
        cal = Calendar.from_ical(response.content)

        eventos = []
        for component in cal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('summary', ''))
                start = component.get('dtstart').dt
                end = component.get('dtend').dt
                if isinstance(start, datetime):
                    start = start.date()
                if isinstance(end, datetime):
                    end = end.date()
                eventos.append({
                    'check_in': start,
                    'check_out': end,
                    'is_reservation': "Reserved" in summary,
                    'external_id': str(component.get('uid')),
                })

        IcalBlock.objects.filter(listing=property_obj).delete()
        IcalBlock.objects.bulk_create([IcalBlock(listing=property_obj, **e) for e in eventos])

        return True, f"{property_obj.name}: {len(eventos)} eventos sincronizados"

    except requests.RequestException as e:
        return False, f"{property_obj.name}: error de conexión — {e}"
    except Exception as e:
        return False, f"{property_obj.name}: error inesperado — {e}"


def sincronizar_todas_las_propiedades():
    """Sincroniza todas las propiedades con iCal configurado. Una falla no detiene a las demás."""
    resultado = {'ok': 0, 'error': 0, 'log': []}
    propiedades = Property.objects.exclude(airbnb_ical_url='')

    for p in propiedades:
        exito, mensaje = sincronizar_ical_propiedad(p)
        resultado['log'].append(mensaje)
        if exito:
            resultado['ok'] += 1
        else:
            resultado['error'] += 1

    return resultado