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


def main(per_client=5, only_unassigned=True, rut_list=None):
    """Asignar ventas existentes a clientes determinísticamente.

    - per_client: cuántas ventas asignar por cliente (int)
    - only_unassigned: si True, solo asigna ventas que no tengan cliente
    - rut_list: lista de RUTs a usar (si None, usamos clientes demo con nombres conocidos)
    """

    if rut_list is None:
        # Usar todos los clientes existentes en la base de datos
        clientes = list(Cliente.objects.all().order_by('id'))
    else:
        clientes = list(Cliente.objects.filter(rut__in=rut_list).order_by('rut'))
    if not clientes:
        print('No se encontraron clientes con los RUTs indicados. Termino.')
        return

    # Query ventas a asignar
    ventas_qs = Venta.objects.order_by('fecha')
    if only_unassigned:
        ventas_qs = ventas_qs.filter(cliente__isnull=True)

    ventas = list(ventas_qs)
    if not ventas:
        print('No hay ventas para asignar según los criterios. Termino.')
        return

    # Reparto round-robin: asignar una venta por cliente en orden hasta cumplir per_client por cliente
    assigned_counts = defaultdict(int)
    total_assigned = 0
    client_count = len(clientes)
    # índices por cliente para contar cuántas asignadas
    client_assigned = [0] * client_count
    v_index = 0
    # recorrer ventas y asignar al siguiente cliente que aún no alcanzó per_client
    for v in ventas:
        # encontrar next cliente disponible
        attempts = 0
        while attempts < client_count:
            idx = v_index % client_count
            if client_assigned[idx] < per_client:
                target = clientes[idx]
                break
            v_index += 1
            attempts += 1
        else:
            # todos los clientes alcanzaron per_client, seguir asignando round-robin
            idx = v_index % client_count
            target = clientes[idx]

        v.cliente = target
        v.save(update_fields=['cliente'])
        assigned_counts[target.rut] += 1
        client_assigned[idx] += 1
        total_assigned += 1
        v_index += 1

    print(f'Ventas procesadas: {len(ventas)}. Total asignadas: {total_assigned}.')
    for rut, cnt in assigned_counts.items():
        cli = Cliente.objects.filter(rut=rut).first()
        print(f'  - {rut} ({cli.nombre if cli else "-"}): {cnt} ventas asignadas')


if __name__ == '__main__':
    # parámetros por defecto: asignar 5 ventas por cliente, solo ventas sin cliente
    main(per_client=5, only_unassigned=True)
