import os
import sys
import django
from collections import defaultdict

# Preparar entorno Django
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings_dev')
django.setup()

from pos.models import Venta, Cliente


def main():
    clientes = list(Cliente.objects.all().order_by('id'))
    ventas = list(Venta.objects.order_by('fecha'))

    if not clientes:
        print('No hay clientes en la base de datos. Nada que hacer.')
        return
    if not ventas:
        print('No hay ventas en la base de datos. Nada que hacer.')
        return

    # Reasignar todas las ventas en round-robin
    for idx, v in enumerate(ventas):
        target = clientes[idx % len(clientes)]
        v.cliente = target
        v.save(update_fields=['cliente'])

    # Resumen
    counts = defaultdict(int)
    for v in Venta.objects.all():
        if v.cliente:
            counts[v.cliente.rut] += 1

    total = sum(counts.values())
    print(f'Total ventas en DB: {Venta.objects.count()}')
    print(f'Total ventas asignadas: {total}')
    for rut, cnt in counts.items():
        cli = Cliente.objects.filter(rut=rut).first()
        print(f'  - {rut} | {cli.nombre if cli else "-"} : {cnt}')


if __name__ == '__main__':
    main()
