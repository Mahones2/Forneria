#!/usr/bin/env python
"""
Script para cargar datos iniciales de ejemplo en producción
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from pos.models import Producto, Cliente, Categoria
from decimal import Decimal

print('🔧 Cargando datos iniciales...')

# Crear categorías
categorias_data = [
    {'nombre': 'Panaderia', 'descripcion': 'Productos de panaderia'},
    {'nombre': 'Pasteleria', 'descripcion': 'Tortas y pasteles'},
    {'nombre': 'Bebidas', 'descripcion': 'Bebidas calientes y frias'},
]

categorias = {}
for cat_data in categorias_data:
    cat, created = Categoria.objects.get_or_create(
        nombre=cat_data['nombre'],
        defaults={'descripcion': cat_data['descripcion']}
    )
    categorias[cat_data['nombre']] = cat
    print(f'{"✅ Creada" if created else "⏭️  Ya existe"} categoria: {cat.nombre}')

# Crear productos
productos_data = [
    {'nombre': 'Pan Marraqueta', 'precio': 500, 'stock': 100, 'categoria': 'Panaderia'},
    {'nombre': 'Pan Hallulla', 'precio': 600, 'stock': 80, 'categoria': 'Panaderia'},
    {'nombre': 'Pan Integral', 'precio': 800, 'stock': 50, 'categoria': 'Panaderia'},
    {'nombre': 'Empanada de Pino', 'precio': 1500, 'stock': 40, 'categoria': 'Panaderia'},
    {'nombre': 'Empanada de Queso', 'precio': 1200, 'stock': 35, 'categoria': 'Panaderia'},
    {'nombre': 'Torta Chocolate', 'precio': 8000, 'stock': 10, 'categoria': 'Pasteleria'},
    {'nombre': 'Torta Tres Leches', 'precio': 9000, 'stock': 8, 'categoria': 'Pasteleria'},
    {'nombre': 'Kuchen de Manzana', 'precio': 6000, 'stock': 12, 'categoria': 'Pasteleria'},
    {'nombre': 'Cafe', 'precio': 1000, 'stock': 100, 'categoria': 'Bebidas'},
    {'nombre': 'Jugo Natural', 'precio': 1500, 'stock': 50, 'categoria': 'Bebidas'},
]

for prod_data in productos_data:
    cat = categorias.get(prod_data['categoria'])
    prod, created = Producto.objects.get_or_create(
        nombre=prod_data['nombre'],
        defaults={
            'precio_venta': Decimal(prod_data['precio']),
            'stock_fisico': prod_data['stock'],
            'categoria': cat
        }
    )
    print(f'{"✅ Creado" if created else "⏭️  Ya existe"} producto: {prod.nombre} - ${prod.precio_venta}')

# Crear clientes de ejemplo
clientes_data = [
    {'nombre': 'Juan Perez', 'rut': '11111111-1', 'email': 'juan@example.com'},
    {'nombre': 'Maria Gonzalez', 'rut': '22222222-2', 'email': 'maria@example.com'},
    {'nombre': 'Pedro Rodriguez', 'rut': '33333333-3', 'email': 'pedro@example.com'},
    {'nombre': 'Ana Martinez', 'rut': '44444444-4', 'email': 'ana@example.com'},
    {'nombre': 'Carlos Silva', 'rut': '55555555-5', 'email': 'carlos@example.com'},
]

for cli_data in clientes_data:
    cli, created = Cliente.objects.get_or_create(
        rut=cli_data['rut'],
        defaults={
            'nombre': cli_data['nombre'],
            'correo': cli_data['email'],
            'telefono': '+56900000000'
        }
    )
    print(f'{"✅ Creado" if created else "⏭️  Ya existe"} cliente: {cli.nombre}')

print('\n🎉 Datos iniciales cargados exitosamente!')
print(f'📦 Productos: {Producto.objects.count()}')
print(f'👥 Clientes: {Cliente.objects.count()}')
print(f'📁 Categorias: {Categoria.objects.count()}')
