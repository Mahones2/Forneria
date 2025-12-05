import os
import sys
import django
from decimal import Decimal

# Ensure project root is on sys.path so 'forneria' settings can be imported
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings_dev')
django.setup()

from pos.models import Venta


def main():
    qs = Venta.objects.select_related('cliente', 'empleado').prefetch_related('detalleventa_set', 'pagos').order_by('-fecha')[:5]
    print('\nLast 5 ventas (most recent first):\n')
    for v in qs:
        cliente = v.cliente.nombre if v.cliente else 'Sin cliente'
        empleado = str(v.empleado) if v.empleado else 'Sin empleado'
        print(f"Venta id={v.id} folio={v.folio} fecha={v.fecha} total={v.total} canal={v.canal_venta}")
        print(f"  Cliente: {cliente} | Empleado: {empleado}")
        detalles = v.detalleventa_set.all()
        for d in detalles:
            print(f"    - {d.producto.nombre} x{d.cantidad} @ {d.precio_unitario}")
        pagos = v.pagos.all()
        for p in pagos:
            print(f"    Pago: {p.monto} metodo={p.metodo} fecha={p.fecha}")
        print('')


if __name__ == '__main__':
    main()
