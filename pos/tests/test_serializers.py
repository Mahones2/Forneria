"""
Pruebas para serializers.py
Testing de validaciones en la capa de serializers (DRF)
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta

from pos.serializers import (
    PagoInputSerializer,
    VentaInputSerializer,
    ClienteSerializer,
    EmpleadoCreateSerializer,
    EmpleadoSerializer,
    ProductoSerializer,
    LoteSerializer
)
from pos.models import Cliente, Categoria, Producto, Lote, Empleado


class PagoInputSerializerTest(TestCase):
    """Pruebas para PagoInputSerializer"""

    def test_pago_valido_efectivo_con_monto_recibido(self):
        """Pago en efectivo válido con monto recibido >= monto"""
        data = {
            'metodo': 'EFE',
            'monto': '10000.00',
            'monto_recibido': '15000.00'
        }
        serializer = PagoInputSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_pago_efectivo_sin_monto_recibido_invalido(self):
        """Pago en efectivo sin monto recibido debe ser inválido"""
        data = {
            'metodo': 'EFE',
            'monto': '10000.00'
        }
        serializer = PagoInputSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('monto_recibido', serializer.errors)

    def test_pago_efectivo_monto_recibido_insuficiente_invalido(self):
        """Pago en efectivo con monto recibido < monto debe ser inválido"""
        data = {
            'metodo': 'EFE',
            'monto': '10000.00',
            'monto_recibido': '5000.00'
        }
        serializer = PagoInputSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('monto_recibido', serializer.errors)

    def test_pago_tarjeta_sin_monto_recibido_valido(self):
        """Pago con tarjeta sin monto recibido debe ser válido"""
        data = {
            'metodo': 'DEB',
            'monto': '10000.00'
        }
        serializer = PagoInputSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_pago_monto_negativo_invalido(self):
        """Pago con monto negativo debe ser inválido"""
        data = {
            'metodo': 'EFE',
            'monto': '-100.00',
            'monto_recibido': '100.00'
        }
        serializer = PagoInputSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_pago_monto_cero_invalido(self):
        """Pago con monto cero debe ser inválido"""
        data = {
            'metodo': 'EFE',
            'monto': '0.00',
            'monto_recibido': '100.00'
        }
        serializer = PagoInputSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class VentaInputSerializerTest(TestCase):
    """Pruebas para VentaInputSerializer"""

    def test_venta_valida_con_items_y_pagos(self):
        """Venta válida con items y pagos"""
        data = {
            'items': [
                {'producto_id': 1, 'cantidad': 2}
            ],
            'pagos': [
                {'metodo': 'EFE', 'monto': '5000.00', 'monto_recibido': '5000.00'}
            ]
        }
        serializer = VentaInputSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_venta_sin_items_invalida(self):
        """Venta sin items debe ser inválida"""
        data = {
            'items': [],
            'pagos': [
                {'metodo': 'EFE', 'monto': '5000.00', 'monto_recibido': '5000.00'}
            ]
        }
        serializer = VentaInputSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('items', serializer.errors)

    def test_venta_sin_pagos_invalida(self):
        """Venta sin pagos debe ser inválida"""
        data = {
            'items': [
                {'producto_id': 1, 'cantidad': 2}
            ],
            'pagos': []
        }
        serializer = VentaInputSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('pagos', serializer.errors)


class ClienteSerializerTest(TestCase):
    """Pruebas para ClienteSerializer"""

    def test_cliente_valido_con_rut(self):
        """Cliente válido con RUT en formato correcto"""
        data = {
            'nombre': 'Juan Pérez',
            'rut': '12.345.678-9',
            'correo': 'juan@correo.com',
            'telefono': '912345678'
        }
        serializer = ClienteSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_cliente_rut_formato_invalido(self):
        """Cliente con RUT en formato inválido"""
        data = {
            'nombre': 'Juan Pérez',
            'rut': '12345678',  # Sin guión
            'correo': 'juan@correo.com'
        }
        serializer = ClienteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('rut', serializer.errors)

    def test_cliente_email_duplicado_invalido(self):
        """Cliente con email duplicado debe ser inválido"""
        Cliente.objects.create(
            nombre='Cliente Existente',
            correo='existente@correo.com',
            rut='12.345.678-9'
        )
        data = {
            'nombre': 'Nuevo Cliente',
            'correo': 'existente@correo.com',
            'rut': '98.765.432-1'
        }
        serializer = ClienteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('correo', serializer.errors)

    def test_cliente_telefono_invalido(self):
        """Cliente con teléfono en formato inválido"""
        data = {
            'nombre': 'Juan Pérez',
            'rut': '12.345.678-9',
            'telefono': '12345'  # Muy corto
        }
        serializer = ClienteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('telefono', serializer.errors)


class EmpleadoSerializerTest(TestCase):
    """Pruebas para EmpleadoCreateSerializer"""

    def test_empleado_create_valido(self):
        """Crear empleado con datos válidos"""
        data = {
            'nombre_completo': 'Ana García',
            'username': 'ana_garcia',
            'password': 'password123',
            'cargo': 'Vendedor'
        }
        serializer = EmpleadoCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_empleado_username_con_espacios_invalido(self):
        """Username con espacios debe ser inválido"""
        data = {
            'nombre_completo': 'Ana García',
            'username': 'ana garcia',  # Con espacio
            'password': 'password123',
            'cargo': 'Vendedor'
        }
        serializer = EmpleadoCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_empleado_username_corto_invalido(self):
        """Username menor a 3 caracteres debe ser inválido"""
        data = {
            'nombre_completo': 'Ana García',
            'username': 'ab',
            'password': 'password123',
            'cargo': 'Vendedor'
        }
        serializer = EmpleadoCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_empleado_username_duplicado_invalido(self):
        """Username duplicado debe ser inválido"""
        User.objects.create_user(username='existente', password='pass123')
        data = {
            'nombre_completo': 'Ana García',
            'username': 'existente',
            'password': 'password123',
            'cargo': 'Vendedor'
        }
        serializer = EmpleadoCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_empleado_password_corto_invalido(self):
        """Contraseña menor a 6 caracteres debe ser inválida"""
        data = {
            'nombre_completo': 'Ana García',
            'username': 'ana_garcia',
            'password': '12345',  # Muy corta
            'cargo': 'Vendedor'
        }
        serializer = EmpleadoCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)


class ProductoSerializerTest(TestCase):
    """Pruebas para ProductoSerializer"""

    def setUp(self):
        """Setup inicial - crear categoría"""
        self.categoria = Categoria.objects.create(nombre='Panadería')

    def test_producto_valido(self):
        """Producto válido con todos los datos correctos"""
        data = {
            'nombre': 'Pan Integral',
            'precio_venta': '1500.00',
            'categoria': self.categoria.id,
            'stock_minimo_global': 5
        }
        serializer = ProductoSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_producto_precio_negativo_invalido(self):
        """Producto con precio negativo debe ser inválido"""
        data = {
            'nombre': 'Pan Integral',
            'precio_venta': '-100.00',
            'categoria': self.categoria.id
        }
        serializer = ProductoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('precio_venta', serializer.errors)

    def test_producto_precio_cero_invalido(self):
        """Producto con precio cero debe ser inválido"""
        data = {
            'nombre': 'Pan Integral',
            'precio_venta': '0.00',
            'categoria': self.categoria.id
        }
        serializer = ProductoSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_producto_stock_minimo_negativo_invalido(self):
        """Producto con stock mínimo negativo debe ser inválido"""
        data = {
            'nombre': 'Pan Integral',
            'precio_venta': '1500.00',
            'categoria': self.categoria.id,
            'stock_minimo_global': -1
        }
        serializer = ProductoSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_producto_codigo_barra_invalido(self):
        """Producto con código de barras inválido"""
        data = {
            'nombre': 'Pan Integral',
            'precio_venta': '1500.00',
            'categoria': self.categoria.id,
            'codigo_barra': '123'  # Muy corto
        }
        serializer = ProductoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('codigo_barra', serializer.errors)


class LoteSerializerTest(TestCase):
    """Pruebas para LoteSerializer"""

    def setUp(self):
        """Setup inicial - crear producto"""
        categoria = Categoria.objects.create(nombre='Panadería')
        self.producto = Producto.objects.create(
            nombre='Pan Integral',
            precio_venta=Decimal('1500.00'),
            categoria=categoria
        )

    def test_lote_valido(self):
        """Lote válido con todos los datos correctos"""
        data = {
            'producto': self.producto.id,
            'numero_lote': 'LOTE-2025-001',
            'fecha_elaboracion': str(date.today()),
            'fecha_caducidad': str(date.today() + timedelta(days=30)),
            'precio_costo_unitario': '800.00',
            'stock_inicial': 100
        }
        serializer = LoteSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_lote_precio_costo_negativo_invalido(self):
        """Lote con precio de costo negativo debe ser inválido"""
        data = {
            'producto': self.producto.id,
            'fecha_caducidad': str(date.today() + timedelta(days=30)),
            'precio_costo_unitario': '-100.00',
            'stock_inicial': 100
        }
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_lote_precio_costo_cero_invalido(self):
        """Lote con precio de costo cero debe ser inválido"""
        data = {
            'producto': self.producto.id,
            'fecha_caducidad': str(date.today() + timedelta(days=30)),
            'precio_costo_unitario': '0.00',
            'stock_inicial': 100
        }
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_lote_stock_negativo_invalido(self):
        """Lote con stock negativo debe ser inválido"""
        data = {
            'producto': self.producto.id,
            'fecha_caducidad': str(date.today() + timedelta(days=30)),
            'precio_costo_unitario': '800.00',
            'stock_inicial': -10
        }
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_lote_stock_mayor_9999_invalido(self):
        """Lote con stock mayor a 9999 debe ser inválido"""
        data = {
            'producto': self.producto.id,
            'fecha_caducidad': str(date.today() + timedelta(days=30)),
            'precio_costo_unitario': '800.00',
            'stock_inicial': 10000
        }
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('stock_inicial', serializer.errors)

    def test_lote_fecha_caducidad_antes_elaboracion_invalido(self):
        """Fecha de caducidad anterior a elaboración debe ser inválida"""
        data = {
            'producto': self.producto.id,
            'fecha_elaboracion': str(date.today()),
            'fecha_caducidad': str(date.today() - timedelta(days=1)),  # Anterior
            'precio_costo_unitario': '800.00',
            'stock_inicial': 100
        }
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('fecha_caducidad', serializer.errors)

    def test_lote_fecha_caducidad_igual_elaboracion_invalido(self):
        """Fecha de caducidad igual a elaboración debe ser inválida"""
        hoy = date.today()
        data = {
            'producto': self.producto.id,
            'fecha_elaboracion': str(hoy),
            'fecha_caducidad': str(hoy),  # Igual
            'precio_costo_unitario': '800.00',
            'stock_inicial': 100
        }
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('fecha_caducidad', serializer.errors)
