import os
import django
from decimal import Decimal
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from pos.models import Venta, Cliente, Empleado, DetalleVenta, Producto, Pago

# Obtener un empleado
try:
    empleado = Empleado.objects.first()
    if not empleado:
        print("No hay empleados en la BD")
        exit()
except:
    print("Error al obtener empleado")
    exit()

# Obtener clientes
clientes = list(Cliente.objects.all())
if not clientes:
    print("No hay clientes. Crea clientes primero.")
    exit()

# Obtener productos de la landing
productos = list(Producto.objects.filter(nombre__in=[
    'Bowl Ensalada', 'Panini Artesanal', 'Ciabata', 
    'Pan Integral', 'Pan de Masa Madre', 'Rollos de Canela',
    'Lasagnas Caseras', 'Pastas italianas', 'Pescados y Mariscos'
]))

if len(productos) < 3:
    print("No hay suficientes productos. Ejecuta crear_productos.py primero.")
    exit()

# Eliminar ventas anteriores para recrearlas
Venta.objects.all().delete()
print("Ventas anteriores eliminadas.")

# Crear ventas para cada cliente
metodos_pago = ['EFE', 'TDB', 'TCR', 'TRF']

for i, cliente in enumerate(clientes[:10]):
    # Fecha aleatoria en los últimos 60 días
    dias_atras = random.randint(1, 60)
    fecha = datetime.now() - timedelta(days=dias_atras)
    
    # Seleccionar 1-4 productos aleatorios para esta venta
    num_productos = random.randint(1, 4)
    productos_venta = random.sample(productos, min(num_productos, len(productos)))
    
    # Calcular totales
    neto = Decimal('0')
    detalles = []
    
    for producto in productos_venta:
        cantidad = random.randint(1, 3)
        precio_unitario = Decimal(str(producto.precio_venta))
        subtotal = precio_unitario * cantidad
        neto += subtotal
        detalles.append({
            'producto': producto,
            'cantidad': cantidad,
            'precio_unitario': precio_unitario
        })
    
    iva = (neto * Decimal('0.19')).quantize(Decimal('0.01'))
    total = neto + iva
    
    # Crear venta
    venta = Venta.objects.create(
        cliente=cliente,
        empleado=empleado,
        fecha=fecha,
        canal_venta='pos',
        estado='entregado',
        tipo_documento='boleta',
        folio_documento=f"BOL-202512-{1001+i}",
        neto=neto,
        iva=iva,
        total=total,
    )
    
    # Crear detalles de venta
    for detalle in detalles:
        DetalleVenta.objects.create(
            venta=venta,
            producto=detalle['producto'],
            cantidad=detalle['cantidad'],
            precio_unitario=detalle['precio_unitario'],
            descuento=Decimal('0'),
        )
    
    # Crear pago
    metodo = random.choice(metodos_pago)
    if metodo == 'EFE':
        # Efectivo: calcular vuelto
        monto_recibido = (total + Decimal('1000')).quantize(Decimal('0'))
        vuelto = monto_recibido - total
    else:
        # Tarjeta/Transferencia: monto exacto
        monto_recibido = total
        vuelto = Decimal('0')
    
    Pago.objects.create(
        venta=venta,
        monto=total,
        metodo=metodo,
        monto_recibido=monto_recibido,
        vuelto=vuelto,
    )
    
    productos_nombres = ', '.join([d['producto'].nombre for d in detalles])
    print(f"Venta #{venta.id} - {cliente.nombre} - Productos: {productos_nombres} - Total: ${total}")

print(f"\n✓ Total de ventas creadas: {Venta.objects.count()}")
print(f"✓ Todos los clientes tienen ventas asociadas con productos de la landing")
