import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from pos.models import Producto, Categoria

# Crear categorías
cat_panes, _ = Categoria.objects.get_or_create(
    nombre="Panadería",
    defaults={"descripcion": "Panes artesanales"}
)

cat_ensaladas, _ = Categoria.objects.get_or_create(
    nombre="Ensaladas",
    defaults={"descripcion": "Ensaladas frescas"}
)

cat_congelados, _ = Categoria.objects.get_or_create(
    nombre="Congelados",
    defaults={"descripcion": "Productos congelados"}
)

# Productos de la landing
productos_data = [
    # Productos Destacados
    {"nombre": "Bowl Ensalada", "precio_venta": Decimal("7500"), "categoria": cat_ensaladas},
    {"nombre": "Panini Artesanal", "precio_venta": Decimal("4500"), "categoria": cat_panes},
    {"nombre": "Ciabata", "precio_venta": Decimal("3800"), "categoria": cat_panes},
    {"nombre": "Pan Integral", "precio_venta": Decimal("3200"), "categoria": cat_panes},
    {"nombre": "Pan de Masa Madre", "precio_venta": Decimal("5000"), "categoria": cat_panes},
    {"nombre": "Rollos de Canela", "precio_venta": Decimal("4200"), "categoria": cat_panes},
    # Congelados
    {"nombre": "Lasagnas Caseras", "precio_venta": Decimal("8500"), "categoria": cat_congelados},
    {"nombre": "Pastas italianas", "precio_venta": Decimal("6500"), "categoria": cat_congelados},
    {"nombre": "Pescados y Mariscos", "precio_venta": Decimal("12000"), "categoria": cat_congelados},
]

for data in productos_data:
    producto, created = Producto.objects.get_or_create(
        nombre=data["nombre"],
        defaults={
            "categoria": data["categoria"],
            "precio_venta": data["precio_venta"],
            "stock_fisico": 100,
        }
    )
    status = "creado" if created else "ya existía"
    print(f"{data['nombre']} - {status}")

print(f"\nTotal de productos: {Producto.objects.count()}")
