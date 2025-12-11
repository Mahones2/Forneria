import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings') 
django.setup()

from pos.models import Lote, Producto

# Ver estructura del modelo Lote
print("Estructura del modelo Lote:\n")
print("Campos disponibles:")
for field in Lote._meta.get_fields():
    print(f"  - {field.name}: {field.__class__.__name__}")

# Ver ejemplo de lotes existentes
print("\n\nEjemplos de lotes existentes:")
lotes = Lote.objects.all()[:5]
for lote in lotes:
    print(f"  Lote ID {lote.id}: Producto {lote.producto.nombre}")
    print(f"    - Stock actual: {lote.stock_actual}/{lote.stock_inicial}")
    print(f"    - Vencimiento: {lote.fecha_caducidad}\n")

# Ver si hay lotes para productos reales
print("\n\nVerificando lotes para productos reales:")
productos_reales = ['Bowl Ensalada', 'Panini Artesanal', 'Ciabata', 'Pan Integral', 'Pan de Masa Madre', 'Rollos de Canela', 'Lasagnas Caseras', 'Pastas Italianas', 'Pescados y Mariscos']

for nombre in productos_reales:
    try:
        producto = Producto.objects.get(nombre=nombre)
        lotes = Lote.objects.filter(producto=producto)
        print(f"\n{nombre}:")
        print(f"  Producto ID: {producto.id}, Stock global: {producto.stock_fisico}")
        print(f"  Lotes: {lotes.count()}")
        if lotes.count() == 0:
            print(f"  --> REQUIERE CREAR LOTES")
        for lote in lotes:
            print(f"    * Lote {lote.id}: {lote.stock_actual}/{lote.stock_inicial} unidades (venc: {lote.fecha_caducidad})")
        print()
    except Producto.DoesNotExist:
        print(f"{nombre}: NO ENCONTRADO\n")
