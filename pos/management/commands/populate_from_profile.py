from django.core.management.base import BaseCommand
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth.models import User
from pos.models import Categoria, Producto, Lote

class Command(BaseCommand):
    help = 'Pobla la base de datos con datos básicos extraídos del perfil entregado (La Fornería)'

    def handle(self, *args, **options):
        created = []

        # Owner / Empleado (no crear como Cliente)
        owner_rut = '77.857.802-6'
        owner_email = 'merino.bellagamba@gmail.com'
        # Crear o actualizar usuario Django para el propietario (administrador)
        user, u_created = User.objects.get_or_create(username='javier.merino', defaults={'email': owner_email})
        if u_created:
            user.set_password('changeme123')
            user.is_staff = True
            user.is_superuser = True
            user.save()
            created.append('User administrador javier.merino')
        else:
            # Si ya existe el usuario, asegurarnos que es administrador
            changed = False
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if changed:
                user.save()
                created.append('User javier.merino actualizado a administrador')

        # Categorías principales extraídas del documento
        categorias = [
            ('Panaderia y Pasteleria', 'Panadería y pastelería artesanal, panes, rollos y pasteles'),
            ('Empanadas', 'Empanadas de horno: pino, mechada, queso, napolitana, vegetariana'),
            ('Cafe y Bebidas', 'Café de especialidad y bebidas'),
            ('Gourmet y Congelados', 'Pastas congeladas, pescados y mariscos, charcuteria, pizzas'),
            ('Opciones Dietéticas', 'Productos sin gluten, veganos, sin azúcar agregado'),
        ]

        cat_objs = {}
        for nombre, desc in categorias:
            obj, created_flag = Categoria.objects.get_or_create(nombre=nombre, defaults={'descripcion': desc})
            cat_objs[nombre] = obj
            if created_flag:
                created.append(f"Categoria {nombre}")

        # Productos de ejemplo basados en la lista del documento (precios estimados)
        productos = [
            ('Pan Hallulla', 'Pan clásico hallulla 1 unidad', 'Panaderia y Pasteleria', 'Pan', 'unidad', '1500.00', 20, 1200.00),
            ('Pan Integral', 'Pan integral por pieza', 'Panaderia y Pasteleria', 'Pan', 'pieza', '1700.00', 15, 1000.00),
            ('Pan Masa Madre', 'Pan masa madre artesanal', 'Panaderia y Pasteleria', 'Pan', 'pieza', '2200.00', 10, 1200.00),
            ('Rollo Canela', 'Rollo de canela glaseado', 'Panaderia y Pasteleria', 'Pastel', 'unidad', '900.00', 30, 300.00),
            ('Empanada Pino', 'Empanada de pino al horno', 'Empanadas', 'Empanada', 'unidad', '1200.00', 50, 400.00),
            ('Empanada Queso', 'Empanada de queso', 'Empanadas', 'Empanada', 'unidad', '1200.00', 40, 400.00),
            ('Cafe Lavazza', 'Café de especialidad (taza)', 'Cafe y Bebidas', 'Bebida', 'taza', '900.00', 999, 100.00),
            ('Pasta Italiana Congelada', 'Paquete de pasta italiana congelada 400g', 'Gourmet y Congelados', 'Pasta', 'paquete', '4990.00', 60, 2500.00),
            ('Pizza Artesanal (congelada)', 'Pizza artesanal lista para hornear', 'Gourmet y Congelados', 'Pizza', 'unidad', '6990.00', 30, 3000.00),
            ('Galletas Chocolate', 'Galletas caseras con chocolate', 'Panaderia y Pasteleria', 'Galleta', 'pack', '1800.00', 25, 600.00),
            ('Producto Sin Gluten Ejemplo', 'Ejemplo sin gluten', 'Opciones Dietéticas', 'Pan', 'unidad', '1900.00', 12, 900.00),
        ]

        for nombre, descripcion, categoria_nombre, tipo, presentacion, precio_str, stock_initial, costo_unit in productos:
            categoria = cat_objs.get(categoria_nombre)
            if not categoria:
                categoria = Categoria.objects.create(nombre=categoria_nombre)
                created.append(f"Categoria {categoria_nombre}")

            prod, p_created = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'descripcion': descripcion,
                    'marca': 'La Fornería',
                    'precio_venta': Decimal(precio_str),
                    'tipo': tipo,
                    'presentacion': presentacion,
                    'categoria': categoria,
                    'costo_unitario': Decimal(str(costo_unit)),
                    'stock_fisico': int(stock_initial),
                }
            )
            if p_created:
                created.append(f"Producto {nombre}")
            else:
                # actualizar algunos campos si ya existe
                prod.descripcion = descripcion
                prod.marca = prod.marca or 'La Fornería'
                prod.precio_venta = Decimal(precio_str)
                prod.tipo = tipo
                prod.presentacion = presentacion
                prod.costo_unitario = Decimal(str(costo_unit))
                prod.categoria = categoria
                prod.stock_fisico = int(stock_initial)
                prod.save()

            # Crear un lote inicial si no existe
            if not prod.lotes.exists():
                lote = Lote.objects.create(
                    producto=prod,
                    numero_lote=f"INIT-{prod.id}-{int(timezone.now().timestamp())}",
                    fecha_elaboracion=timezone.now().date(),
                    fecha_caducidad=(timezone.now() + timedelta(days=30)).date(),
                    precio_costo_unitario=Decimal(str(costo_unit)),
                    stock_inicial=int(stock_initial),
                    stock_actual=int(stock_initial)
                )
                created.append(f"Lote inicial para {prod.nombre}")

        # Resumen
        if created:
            self.stdout.write(self.style.SUCCESS('Se han creado/actualizado los siguientes registros:'))
            for r in created:
                self.stdout.write(f" - {r}")
        else:
            self.stdout.write('No se crearon registros (todo ya existía).')

        self.stdout.write(self.style.NOTICE('Ejecución finalizada.'))
