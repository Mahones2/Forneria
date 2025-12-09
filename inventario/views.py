from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import datetime
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pos.models import Producto, Categoria
from .services import InventarioMetrics


def inventario_list(request):

    categorias = Categoria.objects.all().order_by('nombre')

    contexto = {
        'categorias': categorias,
    }

    return render(request, "inventario/inventario.html", contexto)


def producto_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == "POST":
        producto.delete()
        return redirect("inventario_list")

    return render(request, "inventario/producto_confirm_delete.html", {"producto": producto})


def parse_fecha(fecha_str):
    """Helper para parsear fechas desde query params"""
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def dashboard_inventario(request):
    """
    Vista HTML del dashboard de inventario
    Renderiza template con todas las métricas de inventario
    """
    # Parsear filtros de fecha desde request
    fecha_inicio = parse_fecha(request.GET.get('fecha_inicio'))
    fecha_fin = parse_fecha(request.GET.get('fecha_fin'))

    # Obtener todas las métricas
    kpis = InventarioMetrics.kpis_generales()
    productos_bajo = InventarioMetrics.productos_stock_bajo(limite=10)
    productos_vencer = InventarioMetrics.productos_proximos_vencer(dias=7, limite=10)
    productos_vencidos = InventarioMetrics.productos_vencidos()
    insumos_bajo = InventarioMetrics.insumos_stock_bajo(limite=10)

    ordenes_pendientes = InventarioMetrics.ordenes_compra_pendientes()
    compras_proveedor = InventarioMetrics.compras_por_proveedor(fecha_inicio, fecha_fin)

    movimientos = InventarioMetrics.movimientos_inventario(fecha_inicio, fecha_fin)
    productos_movimiento = InventarioMetrics.productos_mas_movimiento(fecha_inicio, fecha_fin, limite=10)

    stock_categoria = InventarioMetrics.stock_por_categoria()
    valorizacion = InventarioMetrics.valorizacion_por_categoria()

    alertas_resumen = InventarioMetrics.resumen_alertas()
    alertas_activas = InventarioMetrics.alertas_activas(limite=10)

    rotacion = InventarioMetrics.rotacion_inventario(fecha_inicio, fecha_fin)

    # Helper function to convert Decimal to float for JSON serialization
    def clean_for_json(obj):
        """Recursively convert Decimal to float in dict/list structures"""
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(item) for item in obj]
        elif hasattr(obj, '__float__'):
            return float(obj)
        else:
            return obj

    # Preparar alertas para el template
    alertas_dashboard = []

    # Alerta si hay productos vencidos
    if productos_vencidos['cantidad_lotes'] > 0:
        alertas_dashboard.append({
            'tipo': 'danger',
            'titulo': 'Productos Vencidos',
            'mensaje': f'Hay {productos_vencidos["cantidad_lotes"]} lotes vencidos con un valor de ${productos_vencidos["total_valor_perdido"]:,.0f}'
        })

    # Alerta si hay productos por vencer
    if len(productos_vencer) > 0:
        alertas_dashboard.append({
            'tipo': 'warning',
            'titulo': 'Productos Próximos a Vencer',
            'mensaje': f'Hay {len(productos_vencer)} lotes que vencen en los próximos 7 días'
        })

    # Alerta si hay productos con stock bajo
    if kpis['productos_bajo_stock'] > 0:
        alertas_dashboard.append({
            'tipo': 'warning',
            'titulo': 'Stock Bajo',
            'mensaje': f'{kpis["productos_bajo_stock"]} productos tienen stock bajo el mínimo'
        })

    # Alerta si hay insumos con stock bajo
    if kpis['insumos_bajo_stock'] > 0:
        alertas_dashboard.append({
            'tipo': 'info',
            'titulo': 'Insumos con Stock Bajo',
            'mensaje': f'{kpis["insumos_bajo_stock"]} insumos necesitan reposición'
        })

    context = {
        'kpis': kpis,
        'productos_bajo_stock': productos_bajo,
        'productos_vencer': productos_vencer,
        'productos_vencidos': productos_vencidos,
        'insumos_bajo': insumos_bajo,

        'ordenes_pendientes': ordenes_pendientes,
        'compras_proveedor': compras_proveedor,

        'movimientos': movimientos,
        'productos_movimiento': productos_movimiento,

        'stock_categoria': stock_categoria,
        'valorizacion': valorizacion,

        'alertas_resumen': alertas_resumen,
        'alertas_activas': alertas_activas,
        'alertas_dashboard': alertas_dashboard,

        'rotacion': rotacion,

        'fecha_actual': timezone.now().strftime('%d/%m/%Y %H:%M:%S'),
        'fecha_inicio': fecha_inicio.isoformat() if fecha_inicio else '',
        'fecha_fin': fecha_fin.isoformat() if fecha_fin else '',

        # JSON-encoded versions for JavaScript
        'movimientos_json': json.dumps(clean_for_json(movimientos)),
        'stock_categoria_json': json.dumps(clean_for_json(stock_categoria)),
        'compras_proveedor_json': json.dumps(clean_for_json(compras_proveedor)),
        'alertas_resumen_json': json.dumps(clean_for_json(alertas_resumen)),
    }

    return render(request, 'dashboard_inventario.html', context)


@api_view(['GET'])
def dashboard_inventario_api(request):
    """
    GET /dashboard/inventario/
    Endpoint API para el frontend - retorna datos del dashboard de inventario
    """
    # Helper function to convert Decimal to float
    def clean_for_json(obj):
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(item) for item in obj]
        elif hasattr(obj, '__float__'):
            return float(obj)
        else:
            return obj

    # Obtener todas las métricas
    kpis = clean_for_json(InventarioMetrics.kpis_generales())
    productos_bajo = clean_for_json(InventarioMetrics.productos_stock_bajo(limite=10))
    productos_vencer = clean_for_json(InventarioMetrics.productos_proximos_vencer(dias=7, limite=10))
    productos_vencidos = clean_for_json(InventarioMetrics.productos_vencidos())
    stock_categoria = clean_for_json(InventarioMetrics.stock_por_categoria())

    response_data = {
        'kpis': kpis,
        'productos_bajo_stock': productos_bajo,
        'productos_vencer': productos_vencer,
        'productos_vencidos': productos_vencidos,
        'stock_categoria': stock_categoria
    }

    return Response(response_data)
