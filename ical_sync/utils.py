import requests
from icalendar import Calendar
from .models import IcalBlock
from datetime import datetime

def sincronizar_ical_propiedad(property_obj):
    if not property_obj.airbnb_ical_url:
        return

    try:
        response = requests.get(property_obj.airbnb_ical_url, timeout=10)
        cal = Calendar.from_ical(response.content)

        # Limpieza total de la propiedad para evitar conflictos de IDs
        IcalBlock.objects.filter(listing=property_obj).delete()

        for component in cal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('summary', ''))
                start = component.get('dtstart').dt
                end = component.get('dtend').dt
                
                if isinstance(start, datetime): start = start.date()
                if isinstance(end, datetime): end = end.date()

                # Lógica de clasificación:
                # Si dice "Reserved", lo marcamos como reserva real.
                is_res = "Reserved" in summary

                IcalBlock.objects.create(
                    listing=property_obj,
                    check_in=start,
                    check_out=end,
                    is_reservation=is_res,
                    external_id=str(component.get('uid'))
                )
    except Exception as e:
        print(f"Error en {property_obj.name}: {e}")