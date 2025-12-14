"""
Pruebas para models.py
Testing de validaciones en la capa de modelos (Django ORM clean())
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta

from pos.models import Cliente, Categoria, Producto, Lote


class ClienteModelTest(TestCase):
    """Pruebas para modelo Cliente y su método clean()"""

    def test_cliente_rut_valido_se_guarda(self):
        """Cliente con RUT válido debe guardarse correctamente"""
        cliente = Cliente(
            nombre='Juan Pérez',
            rut='12.345.678-9',
            correo='juan@correo.com'
        )
        # No debe lanzar excepción
        cliente.save()
        self.assertIsNotNone(cliente.id)

    def test_cliente_rut_sin_puntos_valido(self):
        """Cliente con RUT sin puntos pero con guión debe guardarse"""
        cliente = Cliente(
            nombre='María López',
            rut='12345678-9',
            correo='maria@correo.com'
        )
        cliente.save()
        self.assertIsNotNone(cliente.id)

    def test_cliente_rut_formato_invalido_lanza_error(self):
        """Cliente con RUT en formato inválido debe lanzar ValidationError"""
        cliente = Cliente(
            nombre='Pedro González',
            rut='12345678',  # Sin guión
            correo='pedro@correo.com'
        )
        with self.assertRaises(ValidationError) as cm:
            cliente.save()
        self.assertIn('rut', cm.exception.message_dict)

    def test_cliente_rut_con_letras_invalido(self):
        """Cliente con RUT con letras (excepto K) debe lanzar error"""
        cliente = Cliente(
            nombre='Ana Torres',
            rut='12.345.678-A',  # A no es válido
            correo='ana@correo.com'
        )
        with self.assertRaises(ValidationError):
            cliente.save()

    def test_cliente_rut_con_k_mayuscula_valido(self):
        """Cliente con RUT con K mayúscula debe guardarse"""
        cliente = Cliente(
            nombre='Carlos Ruiz',
            rut='12.345.678-K',
            correo='carlos@correo.com'
        )
        cliente.save()
        self.assertIsNotNone(cliente.id)

    def test_cliente_rut_con_k_minuscula_valido(self):
        """Cliente con RUT con k minúscula debe guardarse"""
        cliente = Cliente(
            nombre='Laura Díaz',
            rut='12.345.678-k',
            correo='laura@correo.com'
        )
        cliente.save()
        self.assertIsNotNone(cliente.id)

    def test_cliente_sin_rut_valido(self):
        """Cliente sin RUT (null) debe guardarse correctamente"""
        cliente = Cliente(
            nombre='José Vega',
            correo='jose@correo.com'
        )
        cliente.save()
        self.assertIsNotNone(cliente.id)
        self.assertIsNone(cliente.rut)


class ProductoModelTest(TestCase):
    """Pruebas para modelo Producto y su método clean()"""

    def setUp(self):
        """Setup inicial - crear categoría"""
        self.categoria = Categoria.objects.create(nombre='Panadería')

    def test_producto_precio_venta_positivo_valido(self):
        """Producto con precio de venta positivo debe guardarse"""
        producto = Producto(
            nombre='Pan Integral',
            precio_venta=Decimal('1500.00'),
            categoria=self.categoria
        )
        producto.save()
        self.assertIsNotNone(producto.id)
        self.assertEqual(producto.precio_venta, Decimal('1500.00'))

    def test_producto_precio_venta_negativo_invalido(self):
        """Producto con precio de venta negativo debe lanzar error"""
        producto = Producto(
            nombre='Pan Blanco',
            precio_venta=Decimal('-100.00'),
            categoria=self.categoria
        )
        with self.assertRaises(ValidationError) as cm:
            producto.save()
        self.assertIn('precio_venta', cm.exception.message_dict)

    def test_producto_costo_unitario_positivo_valido(self):
        """Producto con costo unitario positivo debe guardarse"""
        producto = Producto(
            nombre='Hallulla',
            precio_venta=Decimal('800.00'),
            costo_unitario=Decimal('400.00'),
            categoria=self.categoria
        )
        producto.save()
        self.assertEqual(producto.costo_unitario, Decimal('400.00'))

    def test_producto_costo_unitario_negativo_invalido(self):
        """Producto con costo unitario negativo debe lanzar error"""
        producto = Producto(
            nombre='Marraqueta',
            precio_venta=Decimal('500.00'),
            costo_unitario=Decimal('-50.00'),
            categoria=self.categoria
        )
        with self.assertRaises(ValidationError) as cm:
            producto.save()
        self.assertIn('costo_unitario', cm.exception.message_dict)

    def test_producto_stock_minimo_positivo_valido(self):
        """Producto con stock mínimo positivo debe guardarse"""
        producto = Producto(
            nombre='Empanada',
            precio_venta=Decimal('1200.00'),
            stock_minimo_global=10,
            categoria=self.categoria
        )
        producto.save()
        self.assertEqual(producto.stock_minimo_global, 10)

    def test_producto_stock_minimo_negativo_invalido(self):
        """Producto con stock mínimo negativo debe lanzar error"""
        producto = Producto(
            nombre='Completo',
            precio_venta=Decimal('2000.00'),
            stock_minimo_global=-5,
            categoria=self.categoria
        )
        with self.assertRaises(ValidationError) as cm:
            producto.save()
        self.assertIn('stock_minimo_global', cm.exception.message_dict)

    def test_producto_stock_minimo_cero_valido(self):
        """Producto con stock mínimo cero debe guardarse"""
        producto = Producto(
            nombre='Sopaipilla',
            precio_venta=Decimal('300.00'),
            stock_minimo_global=0,
            categoria=self.categoria
        )
        producto.save()
        self.assertEqual(producto.stock_minimo_global, 0)


class LoteModelTest(TestCase):
    """Pruebas para modelo Lote y su método clean()"""

    def setUp(self):
        """Setup inicial - crear producto"""
        categoria = Categoria.objects.create(nombre='Panadería')
        self.producto = Producto.objects.create(
            nombre='Pan Integral',
            precio_venta=Decimal('1500.00'),
            categoria=categoria
        )

    def test_lote_fechas_validas_se_guarda(self):
        """Lote con fecha_caducidad > fecha_elaboracion debe guardarse"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-001',
            fecha_elaboracion=date.today(),
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=100
        )
        lote.save()
        self.assertIsNotNone(lote.id)

    def test_lote_fecha_caducidad_antes_elaboracion_invalido(self):
        """Lote con fecha_caducidad < fecha_elaboracion debe lanzar error"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-002',
            fecha_elaboracion=date.today(),
            fecha_caducidad=date.today() - timedelta(days=1),  # Anterior
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=100
        )
        with self.assertRaises(ValidationError) as cm:
            lote.save()
        self.assertIn('fecha_caducidad', cm.exception.message_dict)

    def test_lote_fecha_caducidad_igual_elaboracion_invalido(self):
        """Lote con fecha_caducidad = fecha_elaboracion debe lanzar error"""
        hoy = date.today()
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-003',
            fecha_elaboracion=hoy,
            fecha_caducidad=hoy,  # Igual
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=100
        )
        with self.assertRaises(ValidationError) as cm:
            lote.save()
        self.assertIn('fecha_caducidad', cm.exception.message_dict)

    def test_lote_precio_costo_positivo_valido(self):
        """Lote con precio de costo positivo debe guardarse"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-004',
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('500.00'),
            stock_inicial=50
        )
        lote.save()
        self.assertEqual(lote.precio_costo_unitario, Decimal('500.00'))

    def test_lote_precio_costo_negativo_invalido(self):
        """Lote con precio de costo negativo debe lanzar error"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-005',
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('-100.00'),
            stock_inicial=50
        )
        with self.assertRaises(ValidationError):
            lote.save()

    def test_lote_stock_inicial_valido_en_rango(self):
        """Lote con stock inicial en rango 1-9999 debe guardarse"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-006',
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=5000
        )
        lote.save()
        self.assertEqual(lote.stock_inicial, 5000)

    def test_lote_stock_inicial_negativo_invalido(self):
        """Lote con stock inicial negativo debe lanzar error"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-007',
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=-10
        )
        with self.assertRaises(ValidationError):
            lote.save()

    def test_lote_stock_inicial_mayor_9999_invalido(self):
        """Lote con stock inicial > 9999 debe lanzar error"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-008',
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=10000
        )
        with self.assertRaises(ValidationError):
            lote.save()

    def test_lote_stock_actual_se_inicializa_con_stock_inicial(self):
        """Lote nuevo debe tener stock_actual = stock_inicial"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-009',
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=100
        )
        lote.save()
        self.assertEqual(lote.stock_actual, lote.stock_inicial)

    def test_lote_sin_fecha_elaboracion_valido(self):
        """Lote sin fecha de elaboración (null) debe guardarse"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-2025-010',
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=100
        )
        lote.save()
        self.assertIsNone(lote.fecha_elaboracion)
        self.assertIsNotNone(lote.id)

    def test_lote_update_stock_actual_no_valida(self):
        """Actualización parcial de stock_actual no debe validar clean()"""
        # Crear lote válido
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-2025-011',
            fecha_caducidad=date.today() + timedelta(days=30),
            precio_costo_unitario=Decimal('800.00'),
            stock_inicial=100
        )

        # Actualizar solo stock_actual (como en retirar_stock)
        lote.stock_actual = 50
        lote.save(update_fields=['stock_actual'])

        # Debe guardarse sin problema
        lote.refresh_from_db()
        self.assertEqual(lote.stock_actual, 50)
