import csv
from django.core.management.base import BaseCommand, CommandError
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from pos.models import Producto, Categoria, Lote

class Command(BaseCommand):
    help = 'Reemplaza productos marcados como creados por el poblador y los repuebla desde un CSV.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='Ruta al archivo CSV con productos. Si no se proporciona, usa fixtures/forneria_products_sample.csv')
        parser.add_argument('--dry-run', action='store_true', help='No borra ni crea nada, solo muestra lo que haría')

    def handle(self, *args, **options):
        csv_path = options.get('csv') or 'pos/fixtures/forneria_products_sample.csv'
        dry_run = options.get('dry_run')

        # 1) Identificar productos a eliminar: marca='La Fornería' o que tengan lotes INIT-
        productos_por_marca = Producto.objects.filter(marca__iexact='La Fornería')
        lotes_init = Lote.objects.filter(numero_lote__startswith='INIT-')
        productos_por_lote = Producto.objects.filter(lotes__in=lotes_init).distinct()

        productos_a_eliminar = (productos_por_marca | productos_por_lote).distinct()

        self.stdout.write(self.style.WARNING(f"Productos marcados para eliminación: {productos_a_eliminar.count()}"))
        for p in productos_a_eliminar:
            self.stdout.write(f" - {p.nombre} (id={p.id}) marca={p.marca} stock={p.stock_fisico}")

        if dry_run:
            self.stdout.write(self.style.NOTICE('Dry-run activado. No se realizarán cambios.'))
        else:
            # eliminar lotes relacionados primero
            lote_count = 0
            for lote in lotes_init:
                lote_count += 1
                lote.delete()
            self.stdout.write(self.style.SUCCESS(f"Se eliminaron {lote_count} lotes INIT-"))

            prod_count = productos_a_eliminar.count()
            productos_a_eliminar.delete()
            self.stdout.write(self.style.SUCCESS(f"Se eliminaron {prod_count} productos (marca 'La Fornería' o con lotes INIT-)."))

        # 2) Leer CSV y crear productos
        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"CSV no encontrado en {csv_path}. Crea '{csv_path}' con el template si lo necesitas.")

        created = []
        for row in rows:
            nombre = row.get('nombre') or row.get('Nombre')
            if not nombre:
                self.stderr.write('Fila sin nombre, se omite')
                continue
            descripcion = row.get('descripcion','')
            categoria_nombre = row.get('categoria') or 'Sin categoría'
            precio_str = row.get('precio') or '0'
            stock = int(row.get('stock') or 0)
            costo_str = row.get('costo_unitario') or '0'
            tipo = row.get('tipo','')
            presentacion = row.get('presentacion','')
            caducidad_days = int(row.get('caducidad_days') or 30)

            categoria, _ = Categoria.objects.get_or_create(nombre=categoria_nombre)

            if dry_run:
                self.stdout.write(self.style.NOTICE(f"Crear producto: {nombre} | categoria: {categoria_nombre} | precio: {precio_str} | stock: {stock}"))
                continue

            prod, created_flag = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'descripcion': descripcion,
                    'marca': 'La Fornería',
                    'precio_venta': Decimal(precio_str),
                    'tipo': tipo,
                    'presentacion': presentacion,
                    'categoria': categoria,
                    'costo_unitario': Decimal(costo_str),
                    'stock_fisico': stock,
                }
            )
            if not created_flag:
                # actualizar campos
                prod.descripcion = descripcion
                prod.precio_venta = Decimal(precio_str)
                prod.costo_unitario = Decimal(costo_str)
                prod.tipo = tipo
                prod.presentacion = presentacion
                prod.categoria = categoria
                prod.stock_fisico = stock
                prod.save()

            # crear lote inicial
            lote = Lote.objects.create(
                producto=prod,
                numero_lote=f"INIT-{prod.id}-{int(timezone.now().timestamp())}",
                fecha_elaboracion=timezone.now().date(),
                fecha_caducidad=(timezone.now() + timedelta(days=caducidad_days)).date(),
                precio_costo_unitario=Decimal(costo_str),
                stock_inicial=stock,
                stock_actual=stock
            )
            created.append(f"{prod.nombre} (id={prod.id})")

        self.stdout.write(self.style.SUCCESS(f"Se crearon/actualizaron {len(created)} productos."))
        for c in created:
            self.stdout.write(f" - {c}")
        self.stdout.write(self.style.NOTICE('Proceso finalizado.'))
