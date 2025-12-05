"""
Servicios de métricas para el Dashboard de Inventario
Proporciona KPIs y análisis sobre stock, productos, insumos y órdenes de compra
"""
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db.models import Sum, Count, F, Q, Avg, Max, Min, DecimalField, Value
from django.db.models.functions import Coalesce, TruncDate
from decimal import Decimal

from .models import Insumo, OrdenCompra, OrdenCompraItem, Proveedor
from pos.models import Producto, Lote, MovimientoInventario, Alerta, Categoria


class InventarioMetrics:
    """
    Clase con métodos estáticos para calcular métricas de inventario
    """

    @staticmethod
    def get_date_range(fecha_inicio=None, fecha_fin=None):
        """Helper para obtener rango de fechas por defecto"""
        if not fecha_fin:
            fecha_fin = timezone.now().date()
        if not fecha_inicio:
            fecha_inicio = fecha_fin - timedelta(days=30)
        return fecha_inicio, fecha_fin

    # ==================== KPIs PRINCIPALES ====================

    @staticmethod
    def kpis_generales():
        """
        KPIs generales del inventario
        """
        # Total de productos
        total_productos = Producto.objects.count()

        # Total de lotes activos
        total_lotes = Lote.objects.filter(eliminado__isnull=True).count()

        # Stock total de productos (suma de todos los lotes)
        stock_total_unidades = Lote.objects.filter(
            eliminado__isnull=True
        ).aggregate(total=Sum('stock_actual'))['total'] or 0

        # Valor total del inventario (stock * precio de venta)
        productos_con_stock = Producto.objects.filter(
            lotes__eliminado__isnull=True,
            lotes__stock_actual__gt=0
        ).annotate(
            stock_total=Sum('lotes__stock_actual')
        )

        valor_inventario = sum(
            (p.stock_total or 0) * float(p.precio or 0)
            for p in productos_con_stock
        )

        # Costo total del inventario (stock * costo unitario)
        costo_inventario = sum(
            (p.stock_total or 0) * float(p.costo_unitario or 0)
            for p in productos_con_stock if p.costo_unitario
        )

        # Productos con stock bajo (menor al stock mínimo del lote)
        productos_bajo_stock = Lote.objects.filter(
            eliminado__isnull=True,
            stock_minimo__isnull=False,
            stock_actual__lt=F('stock_minimo')
        ).values('producto').distinct().count()

        # Insumos con stock bajo
        insumos_bajo_stock = Insumo.objects.filter(
            stock_minimo__isnull=False,
            stock_actual__lt=F('stock_minimo')
        ).count()

        return {
            'total_productos': total_productos,
            'total_lotes': total_lotes,
            'stock_total_unidades': int(stock_total_unidades),
            'valor_inventario': round(valor_inventario, 2),
            'costo_inventario': round(costo_inventario, 2),
            'utilidad_potencial': round(valor_inventario - costo_inventario, 2),
            'productos_bajo_stock': productos_bajo_stock,
            'insumos_bajo_stock': insumos_bajo_stock,
        }

    @staticmethod
    def productos_stock_bajo(limite=10):
        """
        Lista de productos con stock bajo
        """
        lotes_bajo = Lote.objects.filter(
            eliminado__isnull=True,
            stock_minimo__isnull=False,
            stock_actual__lt=F('stock_minimo')
        ).select_related('producto', 'producto__categoria').order_by('stock_actual')[:limite]

        resultado = []
        for lote in lotes_bajo:
            resultado.append({
                'producto_id': lote.producto.id,
                'producto_nombre': lote.producto.nombre,
                'categoria': lote.producto.categoria.nombre if lote.producto.categoria else 'Sin categoría',
                'stock_actual': lote.stock_actual,
                'stock_minimo': lote.stock_minimo,
                'numero_lote': lote.numero_lote or f"Lote {lote.id}",
                'diferencia': lote.stock_minimo - lote.stock_actual,
            })

        return resultado

    @staticmethod
    def productos_proximos_vencer(dias=7, limite=10):
        """
        Productos que vencen en los próximos X días
        """
        fecha_limite = date.today() + timedelta(days=dias)

        lotes_proximos = Lote.objects.filter(
            eliminado__isnull=True,
            fecha_caducidad__lte=fecha_limite,
            fecha_caducidad__gte=date.today(),
            stock_actual__gt=0
        ).select_related('producto').order_by('fecha_caducidad')[:limite]

        resultado = []
        for lote in lotes_proximos:
            dias_restantes = (lote.fecha_caducidad - date.today()).days
            resultado.append({
                'producto_nombre': lote.producto.nombre,
                'numero_lote': lote.numero_lote or f"Lote {lote.id}",
                'fecha_caducidad': lote.fecha_caducidad.isoformat(),
                'dias_restantes': dias_restantes,
                'stock_actual': lote.stock_actual,
                'valor_riesgo': round(lote.stock_actual * float(lote.producto.precio or 0), 2),
            })

        return resultado

    @staticmethod
    def productos_vencidos():
        """
        Productos que ya están vencidos y tienen stock
        """
        lotes_vencidos = Lote.objects.filter(
            eliminado__isnull=True,
            fecha_caducidad__lt=date.today(),
            stock_actual__gt=0
        ).select_related('producto').order_by('fecha_caducidad')

        resultado = []
        total_valor_perdido = 0

        for lote in lotes_vencidos:
            valor_perdido = lote.stock_actual * float(lote.producto.precio or 0)
            total_valor_perdido += valor_perdido

            resultado.append({
                'producto_nombre': lote.producto.nombre,
                'numero_lote': lote.numero_lote or f"Lote {lote.id}",
                'fecha_caducidad': lote.fecha_caducidad.isoformat(),
                'dias_vencido': (date.today() - lote.fecha_caducidad).days,
                'stock_actual': lote.stock_actual,
                'valor_perdido': round(valor_perdido, 2),
            })

        return {
            'productos': resultado,
            'total_valor_perdido': round(total_valor_perdido, 2),
            'cantidad_lotes': len(resultado)
        }

    @staticmethod
    def insumos_stock_bajo(limite=10):
        """
        Insumos con stock por debajo del mínimo
        """
        insumos = Insumo.objects.filter(
            stock_minimo__isnull=False,
            stock_actual__lt=F('stock_minimo')
        ).select_related('proveedor').order_by('stock_actual')[:limite]

        resultado = []
        for insumo in insumos:
            resultado.append({
                'nombre': insumo.nombre,
                'unidad_medida': insumo.unidad_medida or 'unidad',
                'stock_actual': float(insumo.stock_actual),
                'stock_minimo': float(insumo.stock_minimo),
                'diferencia': float(insumo.stock_minimo - insumo.stock_actual),
                'proveedor': insumo.proveedor.nombre if insumo.proveedor else 'Sin proveedor',
            })

        return resultado

    # ==================== ÓRDENES DE COMPRA ====================

    @staticmethod
    def ordenes_compra_pendientes():
        """
        Órdenes de compra que están pendientes
        """
        ordenes = OrdenCompra.objects.filter(
            estado='pendiente'
        ).select_related('proveedor').order_by('-fecha')

        resultado = []
        total_pendiente = 0

        for orden in ordenes:
            total_pendiente += float(orden.total)
            resultado.append({
                'id': orden.id,
                'proveedor': orden.proveedor.nombre,
                'fecha': orden.fecha.isoformat(),
                'total': float(orden.total),
                'items_count': orden.items.count(),
            })

        return {
            'ordenes': resultado,
            'total_pendiente': round(total_pendiente, 2),
            'cantidad_ordenes': len(resultado)
        }

    @staticmethod
    def compras_por_proveedor(fecha_inicio=None, fecha_fin=None):
        """
        Total de compras por proveedor en un periodo
        """
        fecha_inicio, fecha_fin = InventarioMetrics.get_date_range(fecha_inicio, fecha_fin)

        compras = OrdenCompra.objects.filter(
            fecha__range=[fecha_inicio, fecha_fin],
            estado='recibida'
        ).values('proveedor__nombre').annotate(
            total=Sum('total'),
            cantidad_ordenes=Count('id')
        ).order_by('-total')

        labels = [c['proveedor__nombre'] or 'Sin proveedor' for c in compras]
        totales = [float(c['total']) for c in compras]
        cantidades = [c['cantidad_ordenes'] for c in compras]

        return {
            'labels': labels,
            'totales': totales,
            'cantidades': cantidades
        }

    # ==================== MOVIMIENTOS DE INVENTARIO ====================

    @staticmethod
    def movimientos_inventario(fecha_inicio=None, fecha_fin=None):
        """
        Movimientos de inventario (entradas y salidas) por día
        """
        fecha_inicio, fecha_fin = InventarioMetrics.get_date_range(fecha_inicio, fecha_fin)

        movimientos = MovimientoInventario.objects.filter(
            fecha__date__range=[fecha_inicio, fecha_fin]
        ).annotate(
            fecha_dia=TruncDate('fecha')
        ).values('fecha_dia', 'tipo_movimiento').annotate(
            total_cantidad=Sum('cantidad')
        ).order_by('fecha_dia', 'tipo_movimiento')

        # Organizar por día
        dias_dict = {}
        for mov in movimientos:
            fecha_str = mov['fecha_dia'].isoformat()
            if fecha_str not in dias_dict:
                dias_dict[fecha_str] = {'entrada': 0, 'salida': 0}
            dias_dict[fecha_str][mov['tipo_movimiento']] = mov['total_cantidad']

        labels = sorted(dias_dict.keys())
        entradas = [dias_dict[fecha]['entrada'] for fecha in labels]
        salidas = [dias_dict[fecha]['salida'] for fecha in labels]

        return {
            'labels': labels,
            'entradas': entradas,
            'salidas': salidas
        }

    @staticmethod
    def productos_mas_movimiento(fecha_inicio=None, fecha_fin=None, limite=10):
        """
        Productos con más movimientos (entradas + salidas)
        """
        fecha_inicio, fecha_fin = InventarioMetrics.get_date_range(fecha_inicio, fecha_fin)

        movimientos = MovimientoInventario.objects.filter(
            fecha__date__range=[fecha_inicio, fecha_fin]
        ).values(
            'producto__nombre',
            'producto__categoria__nombre'
        ).annotate(
            total_movimientos=Sum('cantidad')
        ).order_by('-total_movimientos')[:limite]

        resultado = []
        for mov in movimientos:
            resultado.append({
                'nombre': mov['producto__nombre'],
                'categoria': mov['producto__categoria__nombre'] or 'Sin categoría',
                'total_movimientos': mov['total_movimientos']
            })

        return resultado

    # ==================== DISTRIBUCIÓN POR CATEGORÍA ====================

    @staticmethod
    def stock_por_categoria():
        """
        Stock total y valor por categoría de producto
        """
        categorias = Categoria.objects.annotate(
            total_stock=Sum(
                'producto__lotes__stock_actual',
                filter=Q(producto__lotes__eliminado__isnull=True)
            )
        ).filter(total_stock__gt=0)

        resultado = []
        for cat in categorias:
            # Calcular valor de inventario de esta categoría
            productos = Producto.objects.filter(
                categoria=cat,
                lotes__eliminado__isnull=True,
                lotes__stock_actual__gt=0
            ).annotate(
                stock_total=Sum('lotes__stock_actual')
            )

            valor = sum(
                (p.stock_total or 0) * float(p.precio or 0)
                for p in productos
            )

            resultado.append({
                'categoria': cat.nombre,
                'total_stock': int(cat.total_stock or 0),
                'valor': round(valor, 2)
            })

        # Ordenar por valor descendente
        resultado.sort(key=lambda x: x['valor'], reverse=True)

        labels = [r['categoria'] for r in resultado]
        stocks = [r['total_stock'] for r in resultado]
        valores = [r['valor'] for r in resultado]

        return {
            'labels': labels,
            'stocks': stocks,
            'valores': valores
        }

    # ==================== ALERTAS ====================

    @staticmethod
    def resumen_alertas():
        """
        Resumen de alertas activas por tipo
        """
        alertas = Alerta.objects.values('tipo_alerta').annotate(
            cantidad=Count('id')
        )

        resumen = {
            'verde': 0,
            'amarilla': 0,
            'roja': 0,
            'total': 0
        }

        for alerta in alertas:
            tipo = alerta['tipo_alerta']
            cantidad = alerta['cantidad']
            resumen[tipo] = cantidad
            resumen['total'] += cantidad

        return resumen

    @staticmethod
    def alertas_activas(limite=10):
        """
        Últimas alertas activas
        """
        alertas = Alerta.objects.select_related(
            'producto', 'producto__categoria'
        ).order_by('-fecha_generada')[:limite]

        resultado = []
        for alerta in alertas:
            resultado.append({
                'tipo': alerta.tipo_alerta,
                'mensaje': alerta.mensaje,
                'producto': alerta.producto.nombre,
                'categoria': alerta.producto.categoria.nombre if alerta.producto.categoria else 'Sin categoría',
                'fecha': alerta.fecha_generada.isoformat() if alerta.fecha_generada else None,
                'estado': alerta.estado or 'activa'
            })

        return resultado

    # ==================== ROTACIÓN DE INVENTARIO ====================

    @staticmethod
    def rotacion_inventario(fecha_inicio=None, fecha_fin=None):
        """
        Cálculo de rotación de inventario
        Rotación = Costo de ventas / Inventario promedio
        """
        fecha_inicio, fecha_fin = InventarioMetrics.get_date_range(fecha_inicio, fecha_fin)

        # Calcular costo de ventas (salidas de inventario * costo unitario)
        from pos.models import DetalleVenta, Venta

        ventas = Venta.objects.filter(
            fecha__date__range=[fecha_inicio, fecha_fin]
        )

        costo_ventas = 0
        for venta in ventas:
            for detalle in venta.detalles():
                if detalle.producto.costo_unitario:
                    costo_ventas += detalle.cantidad * float(detalle.producto.costo_unitario)

        # Inventario promedio (simplificado: inventario actual)
        productos_con_stock = Producto.objects.filter(
            lotes__eliminado__isnull=True,
            lotes__stock_actual__gt=0,
            costo_unitario__isnull=False
        ).annotate(
            stock_total=Sum('lotes__stock_actual')
        )

        inventario_promedio = sum(
            (p.stock_total or 0) * float(p.costo_unitario)
            for p in productos_con_stock
        )

        # Calcular rotación
        if inventario_promedio > 0:
            rotacion = costo_ventas / inventario_promedio
            dias_periodo = (fecha_fin - fecha_inicio).days or 1
            # Proyectar a anual
            rotacion_anual = (rotacion * 365) / dias_periodo
        else:
            rotacion = 0
            rotacion_anual = 0

        return {
            'costo_ventas': round(costo_ventas, 2),
            'inventario_promedio': round(inventario_promedio, 2),
            'rotacion': round(rotacion, 2),
            'rotacion_anual': round(rotacion_anual, 2),
            'dias_inventario': round(365 / rotacion_anual, 2) if rotacion_anual > 0 else 0
        }

    # ==================== VALORIZACIÓN ====================

    @staticmethod
    def valorizacion_por_categoria():
        """
        Valorización del inventario por categoría
        """
        categorias = Categoria.objects.all()

        resultado = []
        total_costo = 0
        total_precio = 0

        for cat in categorias:
            productos = Producto.objects.filter(
                categoria=cat,
                lotes__eliminado__isnull=True,
                lotes__stock_actual__gt=0
            ).annotate(
                stock_total=Sum('lotes__stock_actual')
            )

            costo_cat = sum(
                (p.stock_total or 0) * float(p.costo_unitario or 0)
                for p in productos if p.costo_unitario
            )

            precio_cat = sum(
                (p.stock_total or 0) * float(p.precio or 0)
                for p in productos
            )

            if costo_cat > 0 or precio_cat > 0:
                total_costo += costo_cat
                total_precio += precio_cat

                resultado.append({
                    'categoria': cat.nombre,
                    'costo': round(costo_cat, 2),
                    'precio_venta': round(precio_cat, 2),
                    'utilidad_potencial': round(precio_cat - costo_cat, 2),
                    'margen_pct': round(((precio_cat - costo_cat) / precio_cat * 100), 2) if precio_cat > 0 else 0
                })

        # Ordenar por utilidad potencial
        resultado.sort(key=lambda x: x['utilidad_potencial'], reverse=True)

        return {
            'categorias': resultado,
            'total_costo': round(total_costo, 2),
            'total_precio': round(total_precio, 2),
            'total_utilidad_potencial': round(total_precio - total_costo, 2)
        }
