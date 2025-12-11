import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from pos.models import Producto

# Nombres de productos a actualizar
productos_datos = [
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

print("Actualizando stock en la base de datos directamente:\n")

for nombre, stock in productos_datos:
    try:
        producto = Producto.objects.get(nombre=nombre)
        producto.stock_fisico = stock
        producto.save()
        print(f"OK: {nombre:30} -> Stock: {stock}")
    except Producto.DoesNotExist:
        print(f"ERROR: Producto no encontrado: {nombre}")
    except Exception as e:
        print(f"ERROR con {nombre}: {e}")

print("\n Actualizacion completada!")

# Verificar cambios
print("\n Verificacion del stock actualizado:\n")
for nombre, _ in productos_datos:
    try:
        p = Producto.objects.get(nombre=nombre)
        print(f"   {nombre:30} -> {p.stock_fisico} unidades")
    except:
        pass
