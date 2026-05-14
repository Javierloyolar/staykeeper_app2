from django.core.management.base import BaseCommand
from properties.models import Property
from ical_sync.utils import sincronizar_ical_propiedad

class Command(BaseCommand):
    help = 'Sincroniza calendarios de Airbnb para StayKeeper'

    def handle(self, *args, **options):
        propiedades = Property.objects.exclude(airbnb_ical_url='')
        for p in propiedades:
            self.stdout.write(f"Sincronizando {p.name}...")
            sincronizar_ical_propiedad(p)
        self.stdout.write(self.style.SUCCESS("Sincronización completa."))