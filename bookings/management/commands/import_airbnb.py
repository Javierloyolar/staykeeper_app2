from django.core.management.base import BaseCommand
from bookings.services import importar_airbnb_csv


class Command(BaseCommand):
    help = "Importa reservas directamente desde el CSV crudo exportado de Airbnb"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument('--dry-run', action='store_true',
                             help='Simula la importación sin escribir nada en la base de datos')

    def handle(self, *args, **options):
        r = importar_airbnb_csv(options['csv_path'], dry_run=options['dry_run'])

        if r['archivo_error'] or r['columnas_error']:
            self.stderr.write(self.style.ERROR(f"❌ {r['archivo_error'] or r['columnas_error']}"))
            return

        for linea in r['log']:
            self.stdout.write(linea)

        self.stdout.write(self.style.SUCCESS(
            f"\nResumen: {r['creados']} creadas | {r['existentes']} ya existían | "
            f"{r['saltados_listing']} sin listing | {r['saltados_incompletos']} no eran reservas | "
            f"{r['pendientes_nuevas']} pendientes de revisión | {r['saltados_ya_resueltos']} ya resueltos antes | "
            f"{r['saltados_error']} con error"
        ))