from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, F
from datetime import datetime, timedelta
from decimal import Decimal
from pos.models import Venta, Pago, DetalleVenta, Producto, Categoria
from django.db.models.functions import TruncDate, TruncHour

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resumen_financiero(request):
    """
    Retorna dashboard financiero completo filtrado por fecha.
    Parámetros query: fecha_inicio (dd-mm-yyyy), fecha_fin (dd-mm-yyyy)
    """
    try:
        # Obtener fechas de los parámetros o usar hoy
        fecha_inicio_str = request.query_params.get('fecha_inicio')
        fecha_fin_str = request.query_params.get('fecha_fin')
        
        if fecha_inicio_str and fecha_fin_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%d-%m-%Y').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%d-%m-%Y').date()
        else:
            # Por defecto: hoy
            fecha_inicio = datetime.now().date()
            fecha_fin = datetime.now().date()
        
        # Filtrar ventas por rango de fechas
        ventas = Venta.objects.filter(
            fecha__date__gte=fecha_inicio,
            fecha__date__lte=fecha_fin
        )
        
        # Hoy
        hoy = datetime.now().date()
        ventas_hoy = Venta.objects.filter(fecha__date=hoy)
        
        # ========== MÉTRICAS BÁSICAS ==========
        total_ventas = ventas.count()
        total_ventas_hoy = ventas_hoy.count()
        ventas_brutas = float(ventas.aggregate(Sum('total'))['total__sum'] or 0)
        ventas_brutas_hoy = float(ventas_hoy.aggregate(Sum('total'))['total__sum'] or 0)
        
        # IVA y Neto
        total_neto = float(ventas.aggregate(Sum('neto'))['neto__sum'] or 0)
        total_iva = float(ventas.aggregate(Sum('iva'))['iva__sum'] or 0)
        
        # Descuentos
        total_descuentos = float(DetalleVenta.objects.filter(
            venta__fecha__date__gte=fecha_inicio,
            venta__fecha__date__lte=fecha_fin
        ).aggregate(Sum('descuento'))['descuento__sum'] or 0)
        
        # Ticket promedio
        ticket_promedio = ventas_brutas / total_ventas if total_ventas > 0 else 0
        
        # Gastos operativos
        from pos.models import GastoOperativo
        try:
            gastos_operativos = float(GastoOperativo.objects.filter(
                fecha__date__gte=fecha_inicio,
                fecha__date__lte=fecha_fin
            ).aggregate(Sum('monto'))['monto__sum'] or 0)
        except:
            gastos_operativos = 0
        
        # Utilidad
        utilidad_bruta = total_neto
        utilidad_neta = utilidad_bruta - gastos_operativos
        margen_descuento = (total_descuentos / ventas_brutas * 100) if ventas_brutas > 0 else 0
        
        # ========== VENTAS DIARIAS (para gráficos) ==========
        ventas_diarias_data = []
        for i in range((fecha_fin - fecha_inicio).days + 1):
            fecha = fecha_inicio + timedelta(days=i)
            v_dia = Venta.objects.filter(fecha__date=fecha)
            total_dia = float(v_dia.aggregate(Sum('total'))['total__sum'] or 0)
            neto_dia = float(v_dia.aggregate(Sum('neto'))['neto__sum'] or 0)
            iva_dia = float(v_dia.aggregate(Sum('iva'))['iva__sum'] or 0)
            
            ventas_diarias_data.append({
                'fecha': fecha.strftime('%Y-%m-%d'),
                'total': total_dia,
                'netas': neto_dia,
                'iva': iva_dia,
                'cantidad': v_dia.count()
            })
        
        # ========== TOP PRODUCTOS ==========
        productos_top = []
        detalles = DetalleVenta.objects.filter(
            venta__fecha__date__gte=fecha_inicio,
            venta__fecha__date__lte=fecha_fin
        ).values('producto__id', 'producto__nombre', 'producto__categoria__nombre').annotate(
            cantidad=Count('id'),
            ingresos=Sum('precio_unitario')
        ).order_by('-cantidad')[:10]
        
        for d in detalles:
            productos_top.append({
                'nombre': d['producto__nombre'],
                'categoria': d['producto__categoria__nombre'],
                'cantidad_vendida': d['cantidad'],
                'ingresos': float(d['ingresos'] or 0)
            })
        
        # ========== VENTAS POR CATEGORÍA ==========
        ventas_categoria = []
        categorias = DetalleVenta.objects.filter(
            venta__fecha__date__gte=fecha_inicio,
            venta__fecha__date__lte=fecha_fin
        ).values('producto__categoria__nombre').annotate(
            total=Sum('precio_unitario'),
            cantidad=Count('id')
        ).order_by('-total')
        
        for cat in categorias:
            ventas_categoria.append({
                'categoria': cat['producto__categoria__nombre'] or 'Sin categoría',
                'total': float(cat['total'] or 0),
                'cantidad': cat['cantidad']
            })
        
        # ========== VENTAS POR HORA ==========
        ventas_hora = []
        horas = Venta.objects.filter(
            fecha__date__gte=fecha_inicio,
            fecha__date__lte=fecha_fin
        ).annotate(hora=TruncHour('fecha')).values('hora').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('hora')
        
        for h in horas:
            if h['hora']:
                ventas_hora.append({
                    'hora': h['hora'].strftime('%H'),
                    'total': float(h['total'] or 0),
                    'cantidad': h['cantidad']
                })
        
        # ========== VENTAS POR DÍA DE SEMANA ==========
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        ventas_dia_semana = [{
            'dia': dias_semana[i],
            'ventas': 0
        } for i in range(7)]
        
        for venta in ventas:
            dia_semana = venta.fecha.weekday()
            ventas_dia_semana[dia_semana]['ventas'] += float(venta.total)
        
        # Respuesta completa con estructura esperada por frontend
        return Response({
            'kpisHoy': {
                'total': ventas_brutas_hoy,
                'cantidad': total_ventas_hoy,
                'hoy': {
                    'total': ventas_brutas_hoy,
                    'cantidad': total_ventas_hoy
                }
            },
            'resumen': {
                'total_ventas': ventas_brutas,
                'total': ventas_brutas,
                'cantidad_transacciones': total_ventas,
                'cantidad': total_ventas,
                'ticket_promedio': ticket_promedio
            },
            'ventasDiarias': ventas_diarias_data,
            'productosTop': productos_top,
            'ventasPorCategoria': ventas_categoria,
            'ventasPorHora': ventas_hora,
            'ventasDiaSemana': ventas_dia_semana,
            'metricasAvanzadas': {
                'ventas_brutas': ventas_brutas,
                'total_descuentos': total_descuentos,
                'ventas_netas': total_neto,
                'total_iva': total_iva,
                'margen_descuento_pct': margen_descuento
            },
            'utilidadBruta': {
                'utilidad_bruta': utilidad_bruta,
                'margen_bruto_pct': (utilidad_bruta / ventas_brutas * 100) if ventas_brutas > 0 else 0
            },
            'gastosOperativos': {
                'total_gastos': gastos_operativos,
                'desglose': []
            },
            'utilidadNeta': {
                'utilidad_neta': utilidad_neta,
                'margen_neto_pct': (utilidad_neta / ventas_brutas * 100) if ventas_brutas > 0 else 0
            },
            'comparativaMom': [],
            'proyeccion': None,
            'alertas': [],
            'clientesNuevosRecurrentes': None,
            'clientesTop': [],
            'productosRentables': [],
            'flujoCaja': [],
            'roi': {
                'roi': ((utilidad_neta / ventas_brutas) * 100) if ventas_brutas > 0 else 0,
                'utilidad_neta': utilidad_neta,
                'inversion_total': gastos_operativos
            },
            'puntoEquilibrio': {
                'transacciones_equilibrio': 0,
                'monto_equilibrio': 0,
                'progreso_pct': 0
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        return Response({'error': str(e), 'traceback': traceback.format_exc()}, status=status.HTTP_400_BAD_REQUEST)
