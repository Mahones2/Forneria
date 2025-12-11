import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from pos.models import Lote, Producto, Ubicacion

# Datos de productos a los que crear lotes
productos_lotes = [
    ('Bowl Ensalada', 50),
    ('Panini Artesanal', 60),
    ('Ciabata', 80),
    ('Pan Integral', 70),
    ('Pan de Masa Madre', 45),
    ('Rollos de Canela', 90),
    ('Lasagnas Caseras', 30),
    ('Pastas Italianas', 40),
    ('Pescados y Mariscos', 25)
]

# Obtener ubicacion por defecto o la primera disponible
try:
    ubicacion = Ubicacion.objects.first()
    if not ubicacion:
        print("ERROR: No hay ubicaciones disponibles")
        exit(1)
except:
    print("ERROR: No se pudo obtener ubicacion")
    exit(1)

print(f"Ubicacion por defecto: {ubicacion.nombre if ubicacion else 'N/A'}\n")
print("Creando lotes para productos reales:\n")

lotes_creados = 0
fecha_hoy = date.today()
fecha_vencimiento = fecha_hoy + timedelta(days=365)  # Un año de vigencia

for nombre_producto, cantidad in productos_lotes:
    try:
        producto = Producto.objects.get(nombre=nombre_producto)
        
        # Crear el lote
        lote = Lote.objects.create(
            producto=producto,
            numero_lote=f"LOTE-{producto.id}-{fecha_hoy.strftime('%Y%m%d')}",
            fecha_elaboracion=fecha_hoy,
            fecha_caducidad=fecha_vencimiento,
            precio_costo_unitario=producto.precio_costo if producto.precio_costo else 0,
            stock_inicial=cantidad,
            stock_actual=cantidad,
            ubicacion=ubicacion
        )
        
        print(f"OK: {nombre_producto:30} -> Lote creado (ID: {lote.id}, Stock: {cantidad})")
        lotes_creados += 1
        
    except Producto.DoesNotExist:
        print(f"ERROR: Producto no encontrado: {nombre_producto}")
    except Exception as e:
        print(f"ERROR creando lote para {nombre_producto}: {e}")

print(f"\nTotal de lotes creados: {lotes_creados}")
print("Lotes listos para usar en ventas!")
