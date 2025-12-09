from django.core.management.base import BaseCommand
from pos.models import Cliente


class Command(BaseCommand):
    help = 'Asignar o actualizar el nombre de un cliente dado su RUT'

    def add_arguments(self, parser):
        parser.add_argument('rut', type=str, help='RUT del cliente (ej: 11111111-1)')
        parser.add_argument('nombre', type=str, help='Nombre completo a asignar')

    def handle(self, *args, **options):
        rut = options['rut']
        nombre = options['nombre']

        cliente, created = Cliente.objects.get_or_create(rut=rut, defaults={'nombre': nombre})
        if not created:
            cliente.nombre = nombre
            cliente.save(update_fields=['nombre'])
            self.stdout.write(self.style.SUCCESS(f"Actualizado cliente {rut} -> nombre='{nombre}'"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Creado cliente {rut} con nombre='{nombre}'"))
