from django.core.management.base import BaseCommand
from ical_sync.services import sincronizar_todas_las_propiedades


class Command(BaseCommand):
    help = 'Sincroniza calendarios de Airbnb para StayKeeper'

    def handle(self, *args, **options):
        r = sincronizar_todas_las_propiedades()
        for linea in r['log']:
            self.stdout.write(linea)
        self.stdout.write(self.style.SUCCESS(f"\nSincronización completa: {r['ok']} ok | {r['error']} con error"))