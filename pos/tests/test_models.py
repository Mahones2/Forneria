from django.test import TestCase
from django.utils import timezone
from ..models import Categoria, Producto, Lote, Venta, DetalleVenta


class PosModelsTestCase(TestCase):
    def setUp(self):
        # crear categoría
        self.cat = Categoria.objects.create(nombre='Panaderia', descripcion='Productos de pan')
        # crear producto
        self.prod = Producto.objects.create(
            codigo_barra=123456,
            nombre='Pan de molde',
            descripcion='Pan blanco',
            marca='MiPan',
            precio=1000.00,
            tipo='pan',
            presentacion='bolsa',
            formato='500g',
            categoria=self.cat
        )
        # crear lotes
        self.lote1 = Lote.objects.create(producto=self.prod, numero_lote='L1', fecha_caducidad=timezone.now().date(), stock_actual=10, stock_minimo=2, stock_maximo=100)
        self.lote2 = Lote.objects.create(producto=self.prod, numero_lote='L2', fecha_caducidad=timezone.now().date(), stock_actual=5, stock_minimo=1, stock_maximo=50)

    def test_lote_stock_operations_and_estado(self):
        # porcentaje ocupacion
        p = self.lote1.porcentaje_ocupacion()
        self.assertIsNotNone(p)
        # agregar stock
        new = self.lote1.agregar_stock(5)
        self.assertEqual(new, 15)
        # retirar stock
        new2 = self.lote1.retirar_stock(3)
        self.assertEqual(new2, 12)
        # estado
        estado = self.lote1.obtener_estado()
        self.assertIn(estado, ['normal', 'bajo', 'vencido'])

    def test_producto_stock_total_and_precio(self):
        # stock total
        total = self.prod.stock_total()
        self.assertEqual(total, 15)
        # precio final con iva
        pf = self.prod.obtener_precio_final(con_iva=True)
        self.assertTrue(isinstance(pf, float) or isinstance(pf, int))
        # aplicar descuento
        precio_desc = self.prod.aplicar_descuento(10)
        self.assertAlmostEqual(precio_desc, 900.0, places=2)

    def test_venta_calculo_y_actualizar_stock(self):
        # crear venta
        v = Venta.objects.create(fecha=timezone.now(), neto=0, iva=0, total=0, canal_venta='presencial')
        # detalle: 3 unidades
        DetalleVenta.objects.create(cantidad=3, precio_unitario=1000.00, descuento_pct=0, venta=v, producto=self.prod)
        resumen = v.calcular_totales_desde_detalles()
        self.assertIn('total', resumen)
        # actualizar stock (consume lotes)
        v.actualizar_stock()
        self.prod.refresh_from_db()
        # stock total decreased by 3
        self.assertEqual(self.prod.stock_total(), 12)
