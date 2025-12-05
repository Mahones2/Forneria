from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import random
from datetime import timedelta

from pos.models import Categoria, Producto, Lote, Cliente, Empleado, Venta, DetalleVenta, Pago


class Command(BaseCommand):
    help = 'Seed the DB with example POS data (productos, lotes, clientes, empleados y ventas históricas)'

    def handle(self, *args, **options):
        self.stdout.write('Seeding POS data...')

        # Crear categoría
        cat, _ = Categoria.objects.get_or_create(nombre='Panadería', defaults={'descripcion': 'Productos de panadería'})

        # Productos de ejemplo
        productos_data = [
            ('Pan de campo', 1200),
            ('Pancito crujiente', 400),
            ('Empanada de horno (carne)', 900),
            ('Pastel de tres leches', 4500),
            ('Café Lavazza (taza)', 900),
        ]

        productos = []
        for nombre, precio in productos_data:
            p, _ = Producto.objects.get_or_create(nombre=nombre, defaults={
                'precio': Decimal(precio),
                'categoria': cat,
                'descripcion': nombre,
            })
            productos.append(p)

            # Crear un lote para cada producto
            lote_defaults = {
                'numero_lote': f"L-{p.id or 'X'}-{random.randint(100,999)}",
                'fecha_elaboracion': timezone.now().date() - timedelta(days=2),
                'fecha_caducidad': timezone.now().date() + timedelta(days=30),
                'stock_actual': random.randint(20, 120),
                'stock_minimo': 5,
                'stock_maximo': 200,
            }
            Lote.objects.get_or_create(producto=p, numero_lote=lote_defaults['numero_lote'], defaults=lote_defaults)

        # Crear cliente de ejemplo
        cliente, _ = Cliente.objects.get_or_create(rut='11111111-1', defaults={'nombre': 'Cliente Demo', 'correo': 'demo@forneria.local'})

        # Crear empleado
        empleado, _ = Empleado.objects.get_or_create(run='EMP001', defaults={
            'nombres': 'Admin',
            'apellido_paterno': 'Forneria',
            'correo': 'admin@forneria.local',
            'fono': 900000001,
            'clave': 'changeme',
            'direccion': 'Tienda Demo 1',
            'cargo': 'Cajero'
        })

        # Crear ventas históricas
        hoy = timezone.now()
        ventas_creadas = 0
        for i in range(20):
            dias_atras = random.randint(1, 60)
            fecha_venta = hoy - timedelta(days=dias_atras, hours=random.randint(0, 23), minutes=random.randint(0, 59))

            venta = Venta.objects.create(
                fecha=fecha_venta,
                neto=Decimal('0.00'),
                iva=Decimal('0.00'),
                total=Decimal('0.00'),
                canal_venta=random.choice(['presencial', 'delivery']),
                folio_documento=f"F{1000 + i}",
                cliente=cliente,
                empleado=empleado,
            )

            # añadir 1-4 items
            detalles = []
            for _ in range(random.randint(1, 4)):
                producto = random.choice(productos)
                cantidad = random.randint(1, 4)
                precio_unit = producto.precio
                detalle = DetalleVenta.objects.create(
                    cantidad=cantidad,
                    precio_unitario=precio_unit,
                    descuento_pct=None,
                    venta=venta,
                    producto=producto,
                )
                detalles.append(detalle)

            # recalcular totales desde detalles
            totales = venta.calcular_totales_desde_detalles()

            # crear pago (simulado)
            monto_pagado = Decimal(totales['total'])
            Pago.objects.create(venta=venta, monto=monto_pagado, metodo='EFE')

            ventas_creadas += 1

        self.stdout.write(self.style.SUCCESS(f'Creadas {ventas_creadas} ventas de ejemplo.'))