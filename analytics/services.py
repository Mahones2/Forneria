"""
Servicios de métricas para Analytics
Utiliza Django ORM puro para cálculos eficientes
"""
from django.db.models import Sum, Count, Avg, F, Q, DecimalField, Case, When, Max, Min
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek, TruncHour, ExtractHour, ExtractWeekDay, Coalesce
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import calendar

from pos.models import Venta, DetalleVenta, Producto, Categoria, Cliente, GastoOperativo


def _date_to_datetime_range(fecha_inicio, fecha_fin):
    """
    Helper para convertir fechas a rango de datetime timezone-aware
    Resuelve problemas con MySQL y timezone-aware DateTimeFields
    """
    if isinstance(fecha_inicio, date) and not isinstance(fecha_inicio, datetime):
        fecha_inicio = timezone.make_aware(datetime.combine(fecha_inicio, datetime.min.time()))
    elif not fecha_inicio:
        fecha_inicio = timezone.now() - timedelta(days=30)
        fecha_inicio = fecha_inicio.replace(hour=0, minute=0, second=0, microsecond=0)

    if isinstance(fecha_fin, date) and not isinstance(fecha_fin, datetime):
        # Agregar 1 día para incluir todo el día final
        fecha_fin = timezone.make_aware(datetime.combine(fecha_fin + timedelta(days=1), datetime.min.time()))
    elif not fecha_fin:
        fecha_fin = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)

    return fecha_inicio, fecha_fin


class FinanzasMetrics:
    """Métricas financieras avanzadas para dashboard de ventas"""

    @staticmethod
    def resumen_periodo(fecha_inicio=None, fecha_fin=None):
        """
        Resumen general de ventas en un periodo
        Retorna: total_ventas, cantidad_transacciones, ticket_promedio, descuentos_totales
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        resultado = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt,
            fecha__lt=fecha_fin_dt
        ).aggregate(
            total_ventas=Coalesce(Sum('total'), Decimal('0')),
            cantidad_transacciones=Count('id'),
            ticket_promedio=Coalesce(Avg('total'), Decimal('0')),
            neto=Coalesce(Sum('neto'), Decimal('0')),
            total_iva=Coalesce(Sum('iva'), Decimal('0')),
            total_descuentos=Coalesce(Sum('detalles__descuento'), Decimal('0'))
        )

        return {
            'total_ventas': float(resultado['total_ventas']),
            'cantidad_transacciones': resultado['cantidad_transacciones'],
            'ticket_promedio': float(resultado['ticket_promedio']),
            'neto': float(resultado['neto']),
            'total_iva': float(resultado['total_iva']),
            'total_descuentos': float(resultado['total_descuentos']),
            'fecha_inicio': fecha_inicio_dt.date().isoformat() if fecha_inicio_dt else '',
            'fecha_fin': (fecha_fin_dt - timedelta(days=1)).date().isoformat() if fecha_fin_dt else ''
        }

    @staticmethod
    def ventas_diarias(fecha_inicio=None, fecha_fin=None):
        """
        Ventas agrupadas por día para gráfico de líneas
        Formato optimizado para Chart.js
        """
        from django.db.models.functions import Cast
        from django.db.models import DateField

        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        # Usar Cast para convertir datetime a date (compatible con MySQL + timezone)
        ventas = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt,
            fecha__lt=fecha_fin_dt
        ).extra(
            select={'dia': 'DATE(fecha)'}
        ).values('dia').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('dia')

        # Filtrar registros con dia=None
        ventas_list = [v for v in ventas if v['dia'] is not None]

        return {
            'labels': [str(v['dia']) for v in ventas_list],
            'totales': [float(v['total']) for v in ventas_list],
            'cantidades': [v['cantidad'] for v in ventas_list]
        }

    @staticmethod
    def ventas_por_hora():
        """
        Distribución de ventas por hora del día (últimos 7 días)
        """
        fecha_inicio = timezone.now() - timedelta(days=7)

        # Usar HOUR() de MySQL para compatibilidad con timezone
        ventas = Venta.objects.filter(
            fecha__gte=fecha_inicio
        ).extra(
            select={'hora': 'HOUR(fecha)'}
        ).values('hora').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('hora')

        # Llenar horas faltantes con 0
        horas_completas = {h: {'total': 0, 'cantidad': 0} for h in range(24)}
        for v in ventas:
            if v['hora'] is not None:
                hora_int = int(v['hora'])
                horas_completas[hora_int] = {
                    'total': float(v['total']),
                    'cantidad': v['cantidad']
                }

        return {
            'labels': [f"{h:02d}:00" for h in range(24)],
            'totales': [horas_completas[h]['total'] for h in range(24)],
            'cantidades': [horas_completas[h]['cantidad'] for h in range(24)]
        }

    @staticmethod
    def productos_top(limite=10, fecha_inicio=None, fecha_fin=None):
        """
        Top productos más vendidos por cantidad y por ingresos
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)
        filtros = Q(venta__fecha__gte=fecha_inicio_dt, venta__fecha__lt=fecha_fin_dt)

        productos = DetalleVenta.objects.filter(filtros).values(
            'producto__id',
            'producto__nombre',
            'producto__categoria__nombre'
        ).annotate(
            cantidad_vendida=Sum('cantidad'),
            ingresos_totales=Sum(
                F('cantidad') * F('precio_unitario'),
                output_field=DecimalField()
            ),
            num_transacciones=Count('venta', distinct=True)
        ).order_by('-ingresos_totales')[:limite]

        return [{
            'producto_id': p['producto__id'],
            'nombre': p['producto__nombre'],
            'categoria': p['producto__categoria__nombre'],
            'cantidad_vendida': p['cantidad_vendida'],
            'ingresos': float(p['ingresos_totales']),
            'transacciones': p['num_transacciones']
        } for p in productos]

    @staticmethod
    def ventas_por_categoria(fecha_inicio=None, fecha_fin=None):
        """
        Distribución de ventas por categoría de producto
        Para gráfico de dona/pie
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)
        filtros = Q(venta__fecha__gte=fecha_inicio_dt, venta__fecha__lt=fecha_fin_dt)

        categorias = DetalleVenta.objects.filter(filtros).values(
            'producto__categoria__nombre'
        ).annotate(
            total=Sum(
                F('cantidad') * F('precio_unitario'),
                output_field=DecimalField()
            ),
            cantidad_productos=Sum('cantidad')
        ).order_by('-total')

        return {
            'labels': [c['producto__categoria__nombre'] or 'Sin categoría' for c in categorias],
            'totales': [float(c['total']) for c in categorias],
            'cantidades': [c['cantidad_productos'] for c in categorias]
        }

    @staticmethod
    def ventas_por_canal(fecha_inicio=None, fecha_fin=None):
        """
        Comparativa de ventas por canal (presencial vs delivery)
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        canales = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt,
            fecha__lt=fecha_fin_dt
        ).values('canal_venta').annotate(
            total_ventas=Sum('total'),
            cantidad=Count('id'),
            ticket_promedio=Avg('total')
        )

        return [{
            'canal': c['canal_venta'],
            'total': float(c['total_ventas']),
            'cantidad': c['cantidad'],
            'ticket_promedio': float(c['ticket_promedio'])
        } for c in canales]

    @staticmethod
    def comparativa_mensual(meses=6):
        """
        Comparativa de ventas de los últimos N meses
        """
        from datetime import datetime
        fecha_inicio = timezone.now().date() - timedelta(days=meses*30)
        fecha_inicio_dt = timezone.make_aware(datetime.combine(fecha_inicio, datetime.min.time()))

        # Usar DATE_FORMAT para MySQL (compatible con timezone)
        ventas_mensuales = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt
        ).extra(
            select={'mes': "DATE_FORMAT(fecha, '%%Y-%%m-01')"}
        ).values('mes').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('mes')

        # Filtrar None y convertir fechas
        meses_list = [v for v in ventas_mensuales if v['mes'] is not None]

        return {
            'labels': [datetime.strptime(str(v['mes']), '%Y-%m-%d').strftime('%B %Y') if v['mes'] else '' for v in meses_list],
            'totales': [float(v['total']) for v in meses_list],
            'cantidades': [v['cantidad'] for v in meses_list]
        }

    @staticmethod
    def clientes_top(limite=10, fecha_inicio=None, fecha_fin=None):
        """
        Top clientes por volumen de compras
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)
        filtros = Q(cliente__isnull=False)
        filtros &= Q(fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt)

        clientes = Venta.objects.filter(filtros).values(
            'cliente__id',
            'cliente__nombre',
            'cliente__rut'
        ).annotate(
            total_compras=Sum('total'),
            num_compras=Count('id'),
            ticket_promedio=Avg('total')
        ).order_by('-total_compras')[:limite]

        return [{
            'cliente_id': c['cliente__id'],
            'nombre': c['cliente__nombre'] or c['cliente__rut'],
            'rut': c['cliente__rut'],
            'total_compras': float(c['total_compras']),
            'num_compras': c['num_compras'],
            'ticket_promedio': float(c['ticket_promedio'])
        } for c in clientes]

    @staticmethod
    def kpis_hoy():
        """
        KPIs del día actual para cards del dashboard
        """
        # Crear rangos de datetime timezone-aware para hoy y ayer
        ahora = timezone.now()
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        hoy_fin = hoy_inicio + timedelta(days=1)
        ayer_inicio = hoy_inicio - timedelta(days=1)
        ayer_fin = hoy_inicio

        # Ventas de hoy
        hoy_stats = Venta.objects.filter(
            fecha__gte=hoy_inicio,
            fecha__lt=hoy_fin
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id')
        )

        # Ventas de ayer para comparación
        ayer_stats = Venta.objects.filter(
            fecha__gte=ayer_inicio,
            fecha__lt=ayer_fin
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0')),
            cantidad=Count('id')
        )

        # Calcular variación porcentual
        variacion_pct = 0
        if ayer_stats['total'] > 0:
            variacion_pct = ((hoy_stats['total'] - ayer_stats['total']) / ayer_stats['total']) * 100

        return {
            'hoy': {
                'total': float(hoy_stats['total']),
                'cantidad': hoy_stats['cantidad']
            },
            'ayer': {
                'total': float(ayer_stats['total']),
                'cantidad': ayer_stats['cantidad']
            },
            'variacion_pct': float(variacion_pct)
        }

    @staticmethod
    def metricas_avanzadas(fecha_inicio=None, fecha_fin=None):
        """
        Métricas financieras avanzadas del periodo
        Incluye: ventas netas, margen de descuento, tasa de descuento promedio
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        # Calcular descuentos desde los detalles
        total_descuentos_calc = DetalleVenta.objects.filter(
            venta__fecha__gte=fecha_inicio_dt,
            venta__fecha__lt=fecha_fin_dt
        ).aggregate(total=Coalesce(Sum('descuento'), Decimal('0')))['total']

        resultado = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt
        ).aggregate(
            total_neto=Coalesce(Sum('neto'), Decimal('0')),
            total_iva=Coalesce(Sum('iva'), Decimal('0')),
            cantidad_ventas=Count('id')
        )

        # Calcular bruto como neto + descuentos
        total_neto = float(resultado['total_neto'])
        total_descuentos = float(total_descuentos_calc)
        total_bruto = total_neto + total_descuentos

        resultado['total_bruto'] = Decimal(str(total_bruto))
        resultado['total_descuentos'] = Decimal(str(total_descuentos))

        # Cálculos derivados
        total_bruto = float(resultado['total_bruto'])
        total_neto = float(resultado['total_neto'])
        total_descuentos = float(resultado['total_descuentos'])
        total_iva = float(resultado['total_iva'])
        cantidad_ventas = resultado['cantidad_ventas']

        margen_descuento = (total_descuentos / total_bruto * 100) if total_bruto > 0 else 0
        tasa_descuento_promedio = (total_descuentos / cantidad_ventas) if cantidad_ventas > 0 else 0

        return {
            'ventas_brutas': total_bruto,
            'ventas_netas': total_neto,
            'total_descuentos': total_descuentos,
            'total_iva': total_iva,
            'margen_descuento_pct': margen_descuento,
            'descuento_promedio_transaccion': tasa_descuento_promedio,
            'cantidad_ventas': cantidad_ventas,
            'fecha_inicio': fecha_inicio_dt.date().isoformat(),
            'fecha_fin': (fecha_fin_dt - timedelta(days=1)).date().isoformat()
        }

    @staticmethod
    def ticket_promedio_segmentado(fecha_inicio=None, fecha_fin=None):
        """
        Ticket promedio segmentado por canal y por día de semana
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        # Por canal
        por_canal = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt
        ).values('canal_venta').annotate(
            ticket_promedio=Avg('total'),
            cantidad=Count('id')
        )

        # Por día de semana - usar DAYOFWEEK() de MySQL (1=Domingo, 7=Sábado)
        por_dia_semana = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt
        ).extra(
            select={'dia_semana': 'DAYOFWEEK(fecha)'}
        ).values('dia_semana').annotate(
            ticket_promedio=Avg('total'),
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('dia_semana')

        dias_semana_nombres = {
            1: 'Domingo', 2: 'Lunes', 3: 'Martes', 4: 'Miércoles',
            5: 'Jueves', 6: 'Viernes', 7: 'Sábado'
        }

        # Filtrar None
        por_dia_semana_list = [d for d in por_dia_semana if d['dia_semana'] is not None]

        return {
            'por_canal': [{
                'canal': c['canal_venta'],
                'ticket_promedio': float(c['ticket_promedio']),
                'cantidad': c['cantidad']
            } for c in por_canal],
            'por_dia_semana': [{
                'dia': dias_semana_nombres.get(int(d['dia_semana']), 'Desconocido'),
                'dia_numero': int(d['dia_semana']),
                'ticket_promedio': float(d['ticket_promedio']),
                'total': float(d['total']),
                'cantidad': d['cantidad']
            } for d in por_dia_semana_list]
        }

    @staticmethod
    def ventas_por_dia_semana(fecha_inicio=None, fecha_fin=None):
        """
        Distribución de ventas por día de la semana
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        # Usar DAYOFWEEK() de MySQL (1=Domingo, 7=Sábado)
        ventas = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt
        ).extra(
            select={'dia_semana': 'DAYOFWEEK(fecha)'}
        ).values('dia_semana').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('dia_semana')

        dias_semana_nombres = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

        # Inicializar todos los días con 0
        resultado = {i+1: {'total': 0, 'cantidad': 0} for i in range(7)}

        for v in ventas:
            if v['dia_semana'] is not None:
                dia_int = int(v['dia_semana'])
                resultado[dia_int] = {
                    'total': float(v['total']),
                    'cantidad': v['cantidad']
                }

        return {
            'labels': dias_semana_nombres,
            'totales': [resultado[i+1]['total'] for i in range(7)],
            'cantidades': [resultado[i+1]['cantidad'] for i in range(7)]
        }

    @staticmethod
    def clientes_nuevos_vs_recurrentes(fecha_inicio=None, fecha_fin=None):
        """
        Análisis de clientes nuevos vs recurrentes en el periodo
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)
        fecha_inicio_date = fecha_inicio_dt.date()

        # Ventas del periodo con cliente
        ventas_periodo = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt,
            cliente__isnull=False
        )

        # Agrupar por cliente
        clientes_stats = ventas_periodo.values('cliente').annotate(
            num_compras=Count('id'),
            total_gastado=Sum('total'),
            primera_compra=Min('fecha')
        )

        nuevos = 0
        recurrentes = 0
        total_nuevos = Decimal('0')
        total_recurrentes = Decimal('0')

        for c in clientes_stats:
            # Si la primera compra fue en este periodo y solo tiene 1 compra, es nuevo
            if c['primera_compra'].date() >= fecha_inicio_date and c['num_compras'] == 1:
                nuevos += 1
                total_nuevos += c['total_gastado']
            else:
                recurrentes += 1
                total_recurrentes += c['total_gastado']

        return {
            'nuevos': {
                'cantidad': nuevos,
                'total_ventas': float(total_nuevos),
                'promedio': float(total_nuevos / nuevos) if nuevos > 0 else 0
            },
            'recurrentes': {
                'cantidad': recurrentes,
                'total_ventas': float(total_recurrentes),
                'promedio': float(total_recurrentes / recurrentes) if recurrentes > 0 else 0
            }
        }

    @staticmethod
    def heatmap_ventas_hora_dia(fecha_inicio=None, fecha_fin=None):
        """
        Heatmap de ventas: matriz de horas (0-23) x días de semana (Lun-Dom)
        Para visualizar patrones de venta por hora y día
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        # Usar HOUR() y DAYOFWEEK() de MySQL
        ventas = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt
        ).extra(
            select={
                'hora': 'HOUR(fecha)',
                'dia_semana': 'DAYOFWEEK(fecha)'
            }
        ).values('hora', 'dia_semana').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        )

        # Crear matriz 24h x 7 días
        heatmap = {}
        for hora in range(24):
            heatmap[hora] = {dia: {'total': 0, 'cantidad': 0} for dia in range(1, 8)}

        for v in ventas:
            # Filtrar registros con hora o dia_semana None
            if v['hora'] is not None and v['dia_semana'] is not None:
                hora_int = int(v['hora'])
                dia_int = int(v['dia_semana'])
                heatmap[hora_int][dia_int] = {
                    'total': float(v['total']),
                    'cantidad': v['cantidad']
                }

        # Convertir a formato para Chart.js heatmap
        dias_nombres = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

        return {
            'horas': [f"{h:02d}:00" for h in range(24)],
            'dias': dias_nombres,
            'data': [
                {
                    'hora': f"{hora:02d}:00",
                    'dia': dias_nombres[dia-1],
                    'total': heatmap[hora][dia]['total'],
                    'cantidad': heatmap[hora][dia]['cantidad']
                }
                for hora in range(24) for dia in range(1, 8)
            ]
        }

    @staticmethod
    def proyeccion_ventas(dias_proyeccion=7):
        """
        Proyección simple de ventas basada en promedio de últimos 30 días
        """
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=30)

        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        # Promedio diario de los últimos 30 días
        promedio_diario = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0'))
        )

        promedio = float(promedio_diario['total']) / 30

        # Proyectar próximos días
        proyecciones = []
        for i in range(1, dias_proyeccion + 1):
            fecha_proyectada = fecha_fin + timedelta(days=i)
            proyecciones.append({
                'fecha': fecha_proyectada.isoformat(),
                'proyeccion': round(promedio, 2)
            })

        return {
            'promedio_diario': round(promedio, 2),
            'proyecciones': proyecciones
        }

    @staticmethod
    def comparativa_mom(meses=6):
        """
        Comparativa Month-over-Month (MoM)
        Muestra crecimiento/decrecimiento porcentual mes a mes
        """
        from datetime import datetime
        fecha_inicio = timezone.now().date() - timedelta(days=meses*30)
        fecha_inicio_dt = timezone.make_aware(datetime.combine(fecha_inicio, datetime.min.time()))

        # Usar DATE_FORMAT para MySQL (compatible con timezone)
        ventas_mensuales = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt
        ).extra(
            select={'mes': "DATE_FORMAT(fecha, '%%Y-%%m-01')"}
        ).values('mes').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('mes')

        # Filtrar None
        meses_data = [v for v in ventas_mensuales if v['mes'] is not None]

        # Calcular variación MoM
        for i in range(1, len(meses_data)):
            mes_anterior = float(meses_data[i-1]['total'])
            mes_actual = float(meses_data[i]['total'])

            variacion = 0
            if mes_anterior > 0:
                variacion = ((mes_actual - mes_anterior) / mes_anterior) * 100

            meses_data[i]['variacion_mom'] = round(variacion, 2)

        # El primer mes no tiene comparación
        if len(meses_data) > 0:
            meses_data[0]['variacion_mom'] = 0

        return [{
            'mes': datetime.strptime(str(m['mes']), '%Y-%m-%d').strftime('%B %Y') if m['mes'] else '',
            'total': float(m['total']),
            'cantidad': m['cantidad'],
            'variacion_mom': m.get('variacion_mom', 0)
        } for m in meses_data]

    @staticmethod
    def alertas_automaticas(fecha_inicio=None, fecha_fin=None):
        """
        Sistema de alertas automáticas basado en métricas
        Detecta: caída de ventas, bajo rendimiento, productos sin vender, etc.
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)
        fecha_inicio_date = fecha_inicio_dt.date()
        fecha_fin_date = (fecha_fin_dt - timedelta(days=1)).date()

        alertas = []

        # 1. Alerta: Caída de ventas respecto a semana anterior
        semana_anterior_inicio = fecha_inicio_date - timedelta(days=7)
        semana_anterior_fin = fecha_inicio_date - timedelta(days=1)
        semana_anterior_inicio_dt, semana_anterior_fin_dt = _date_to_datetime_range(semana_anterior_inicio, semana_anterior_fin)

        ventas_actuales = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0')))

        ventas_anteriores = Venta.objects.filter(
            fecha__gte=semana_anterior_inicio_dt, fecha__lt=semana_anterior_fin_dt
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0')))

        if ventas_anteriores['total'] > 0:
            variacion = ((ventas_actuales['total'] - ventas_anteriores['total']) / ventas_anteriores['total']) * 100

            if variacion < -10:
                alertas.append({
                    'tipo': 'danger',
                    'titulo': 'Caída en ventas',
                    'mensaje': f'Las ventas han caído un {abs(variacion):.1f}% respecto a la semana anterior',
                    'valor': float(variacion)
                })
            elif variacion > 20:
                alertas.append({
                    'tipo': 'success',
                    'titulo': 'Incremento en ventas',
                    'mensaje': f'Las ventas han aumentado un {variacion:.1f}% respecto a la semana anterior',
                    'valor': float(variacion)
                })

        # 2. Alerta: Productos sin vender en el periodo
        productos_vendidos = DetalleVenta.objects.filter(
            venta__fecha__gte=fecha_inicio_dt, venta__fecha__lt=fecha_fin_dt
        ).values_list('producto_id', flat=True).distinct()

        total_productos = Producto.objects.count()
        productos_sin_venta = total_productos - len(productos_vendidos)

        if productos_sin_venta > 0:
            alertas.append({
                'tipo': 'warning',
                'titulo': 'Productos sin ventas',
                'mensaje': f'{productos_sin_venta} productos no se han vendido en los últimos 7 días',
                'valor': productos_sin_venta
            })

        # 3. Alerta: Días sin ventas
        dias_sin_ventas = 0
        for i in range((fecha_fin_date - fecha_inicio_date).days + 1):
            dia = fecha_inicio_date + timedelta(days=i)
            dia_inicio_dt = timezone.make_aware(datetime.combine(dia, datetime.min.time()))
            dia_fin_dt = dia_inicio_dt + timedelta(days=1)
            ventas_dia = Venta.objects.filter(fecha__gte=dia_inicio_dt, fecha__lt=dia_fin_dt).count()
            if ventas_dia == 0:
                dias_sin_ventas += 1

        if dias_sin_ventas > 0:
            alertas.append({
                'tipo': 'warning',
                'titulo': 'Días sin ventas',
                'mensaje': f'Hubo {dias_sin_ventas} días sin ventas en los últimos 7 días',
                'valor': dias_sin_ventas
            })

        # 4. Alerta: Ticket promedio bajo
        ticket_actual = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt
        ).aggregate(promedio=Avg('total'))

        ticket_historico = Venta.objects.filter(
            fecha__lt=fecha_inicio_dt
        ).aggregate(promedio=Avg('total'))

        if ticket_actual['promedio'] and ticket_historico['promedio']:
            # Convertir a float para evitar errores de tipo Decimal
            ticket_actual_val = float(ticket_actual['promedio'])
            ticket_historico_val = float(ticket_historico['promedio'])

            if ticket_actual_val < ticket_historico_val * 0.8:
                alertas.append({
                    'tipo': 'warning',
                    'titulo': 'Ticket promedio bajo',
                    'mensaje': f'El ticket promedio actual (${ticket_actual_val:.0f}) es significativamente menor al histórico (${ticket_historico_val:.0f})',
                    'valor': ticket_actual_val
                })

        return alertas

    # === NUEVAS MÉTRICAS FINANCIERAS ===

    @staticmethod
    def costo_ventas(fecha_inicio=None, fecha_fin=None):
        """
        Calcula el Costo de Ventas (COGS - Cost of Goods Sold)
        Suma de (cantidad vendida * costo unitario) para todos los productos vendidos
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        # Solo considerar productos que tienen costo_unitario definido
        cogs = DetalleVenta.objects.filter(
            venta__fecha__gte=fecha_inicio_dt,
            venta__fecha__lt=fecha_fin_dt,
            producto__costo_unitario__isnull=False
        ).aggregate(
            total_costo=Coalesce(
                Sum(F('cantidad') * F('producto__costo_unitario'), output_field=DecimalField()),
                Decimal('0')
            )
        )

        return float(cogs['total_costo'])

    @staticmethod
    def utilidad_bruta(fecha_inicio=None, fecha_fin=None):
        """
        Utilidad Bruta = Ventas Totales - Costo de Ventas (COGS)
        """
        resumen = FinanzasMetrics.resumen_periodo(fecha_inicio, fecha_fin)
        costo = FinanzasMetrics.costo_ventas(fecha_inicio, fecha_fin)

        ventas_totales = resumen['neto']  # Sin IVA para cálculo correcto
        utilidad = ventas_totales - costo

        return {
            'ventas_totales': ventas_totales,
            'costo_ventas': costo,
            'utilidad_bruta': utilidad,
            'margen_bruto_pct': round((utilidad / ventas_totales * 100), 2) if ventas_totales > 0 else 0
        }

    @staticmethod
    def gastos_operativos(fecha_inicio=None, fecha_fin=None):
        """
        Suma total de gastos operativos en el período
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)
        # Para GastoOperativo que usa DateField, extraemos solo la fecha
        fecha_inicio_date = fecha_inicio_dt.date()
        fecha_fin_date = (fecha_fin_dt - timedelta(days=1)).date()

        gastos = GastoOperativo.objects.filter(
            fecha__gte=fecha_inicio_date,
            fecha__lte=fecha_fin_date
        ).aggregate(
            total_gastos=Coalesce(Sum('monto'), Decimal('0'))
        )

        # Desglose por tipo de gasto
        por_tipo = GastoOperativo.objects.filter(
            fecha__gte=fecha_inicio_date,
            fecha__lte=fecha_fin_date
        ).values('tipo_gasto').annotate(
            total=Sum('monto')
        ).order_by('-total')

        return {
            'total_gastos': float(gastos['total_gastos']),
            'desglose': [{
                'tipo': g['tipo_gasto'],
                'monto': float(g['total'])
            } for g in por_tipo]
        }

    @staticmethod
    def utilidad_neta(fecha_inicio=None, fecha_fin=None):
        """
        Utilidad Neta = Utilidad Bruta - Gastos Operativos
        Métrica clave para medir la rentabilidad real del negocio
        """
        utilidad_bruta = FinanzasMetrics.utilidad_bruta(fecha_inicio, fecha_fin)
        gastos = FinanzasMetrics.gastos_operativos(fecha_inicio, fecha_fin)

        utilidad_neta_valor = utilidad_bruta['utilidad_bruta'] - gastos['total_gastos']

        return {
            'ventas_totales': utilidad_bruta['ventas_totales'],
            'costo_ventas': utilidad_bruta['costo_ventas'],
            'utilidad_bruta': utilidad_bruta['utilidad_bruta'],
            'gastos_operativos': gastos['total_gastos'],
            'utilidad_neta': utilidad_neta_valor,
            'margen_utilidad_neta_pct': round((utilidad_neta_valor / utilidad_bruta['ventas_totales'] * 100), 2) if utilidad_bruta['ventas_totales'] > 0 else 0
        }

    @staticmethod
    def roi(fecha_inicio=None, fecha_fin=None):
        """
        Return on Investment (ROI)
        ROI = (Utilidad Neta / Inversión Total) * 100
        Inversión Total = Costo de Ventas + Gastos Operativos
        """
        utilidad = FinanzasMetrics.utilidad_neta(fecha_inicio, fecha_fin)

        inversion_total = utilidad['costo_ventas'] + utilidad['gastos_operativos']

        if inversion_total > 0:
            roi_valor = (utilidad['utilidad_neta'] / inversion_total) * 100
        else:
            roi_valor = 0

        return {
            'utilidad_neta': utilidad['utilidad_neta'],
            'inversion_total': inversion_total,
            'roi_porcentaje': round(roi_valor, 2)
        }

    @staticmethod
    def punto_equilibrio(fecha_inicio=None, fecha_fin=None):
        """
        Punto de Equilibrio = Gastos Fijos / Margen de Contribución Promedio
        Indica cuántas ventas se necesitan para cubrir los gastos
        """
        gastos = FinanzasMetrics.gastos_operativos(fecha_inicio, fecha_fin)
        utilidad_bruta = FinanzasMetrics.utilidad_bruta(fecha_inicio, fecha_fin)
        resumen = FinanzasMetrics.resumen_periodo(fecha_inicio, fecha_fin)

        # Margen de contribución promedio por transacción
        if resumen['cantidad_transacciones'] > 0:
            margen_contribucion_unitario = utilidad_bruta['utilidad_bruta'] / resumen['cantidad_transacciones']
        else:
            margen_contribucion_unitario = 0

        # Punto de equilibrio en cantidad de transacciones
        if margen_contribucion_unitario > 0:
            transacciones_equilibrio = gastos['total_gastos'] / margen_contribucion_unitario
            monto_equilibrio = transacciones_equilibrio * resumen['ticket_promedio']
        else:
            transacciones_equilibrio = 0
            monto_equilibrio = 0

        return {
            'gastos_fijos': gastos['total_gastos'],
            'margen_contribucion_unitario': round(margen_contribucion_unitario, 2),
            'transacciones_necesarias': round(transacciones_equilibrio, 0),
            'monto_ventas_necesario': round(monto_equilibrio, 2),
            'transacciones_actuales': resumen['cantidad_transacciones'],
            'porcentaje_alcanzado': round((resumen['cantidad_transacciones'] / transacciones_equilibrio * 100), 2) if transacciones_equilibrio > 0 else 0
        }

    @staticmethod
    def productos_rentables(limite=20, fecha_inicio=None, fecha_fin=None):
        """
        Análisis de rentabilidad real por producto
        Calcula: ingresos, costos, utilidad bruta, margen bruto % para cada producto
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)

        filtros = Q(producto__costo_unitario__isnull=False)
        filtros &= Q(venta__fecha__gte=fecha_inicio_dt, venta__fecha__lt=fecha_fin_dt)

        productos = DetalleVenta.objects.filter(filtros).values(
            'producto__id',
            'producto__nombre',
            'producto__categoria__nombre',
            'producto__precio_venta',
            'producto__costo_unitario'
        ).annotate(
            cantidad_vendida=Sum('cantidad'),
            ingresos_totales=Sum(
                F('cantidad') * F('precio_unitario'),
                output_field=DecimalField()
            ),
            costo_total=Sum(
                F('cantidad') * F('producto__costo_unitario'),
                output_field=DecimalField()
            )
        ).order_by('-ingresos_totales')[:limite]

        resultado = []
        for p in productos:
            ingresos = float(p['ingresos_totales'])
            costo = float(p['costo_total'])
            utilidad = ingresos - costo
            margen_pct = (utilidad / ingresos * 100) if ingresos > 0 else 0

            resultado.append({
                'producto_id': p['producto__id'],
                'nombre': p['producto__nombre'],
                'categoria': p['producto__categoria__nombre'],
                'cantidad_vendida': p['cantidad_vendida'],
                'precio_venta': float(p['producto__precio_venta']),
                'costo_unitario': float(p['producto__costo_unitario']),
                'ingresos_totales': ingresos,
                'costo_total': costo,
                'utilidad_bruta': utilidad,
                'margen_bruto_pct': round(margen_pct, 2)
            })

        return resultado

    @staticmethod
    def flujo_caja(fecha_inicio=None, fecha_fin=None):
        """
        Análisis de flujo de caja: Ingresos vs Gastos
        """
        fecha_inicio_dt, fecha_fin_dt = _date_to_datetime_range(fecha_inicio, fecha_fin)
        fecha_inicio_date = fecha_inicio_dt.date()
        fecha_fin_date = (fecha_fin_dt - timedelta(days=1)).date()

        # Ingresos por día (usar DATE() para MySQL + timezone)
        ingresos = Venta.objects.filter(
            fecha__gte=fecha_inicio_dt,
            fecha__lt=fecha_fin_dt
        ).extra(
            select={'dia': 'DATE(fecha)'}
        ).values('dia').annotate(
            total=Sum('total')
        ).order_by('dia')

        # Gastos por día
        gastos = GastoOperativo.objects.filter(
            fecha__gte=fecha_inicio_date,
            fecha__lte=fecha_fin_date
        ).values('fecha').annotate(
            total=Sum('monto')
        ).order_by('fecha')

        # Crear diccionario de todos los días
        dias_dict = {}
        current_date = fecha_inicio_date
        while current_date <= fecha_fin_date:
            dias_dict[current_date.isoformat()] = {'ingresos': 0, 'gastos': 0}
            current_date += timedelta(days=1)

        # Llenar ingresos
        for i in ingresos:
            if i['dia'] is not None:
                dia_str = str(i['dia']) if not isinstance(i['dia'], str) else i['dia']
                if dia_str in dias_dict:
                    dias_dict[dia_str]['ingresos'] = float(i['total'])

        # Llenar gastos
        for g in gastos:
            if g['fecha'] is not None:
                dias_dict[g['fecha'].isoformat()]['gastos'] = float(g['total'])

        # Calcular flujo neto
        flujo_data = []
        for dia in sorted(dias_dict.keys()):
            flujo_neto = dias_dict[dia]['ingresos'] - dias_dict[dia]['gastos']
            flujo_data.append({
                'fecha': dia,
                'ingresos': dias_dict[dia]['ingresos'],
                'gastos': dias_dict[dia]['gastos'],
                'flujo_neto': flujo_neto
            })

        return {
            'labels': [d['fecha'] for d in flujo_data],
            'ingresos': [d['ingresos'] for d in flujo_data],
            'gastos': [d['gastos'] for d in flujo_data],
            'flujo_neto': [d['flujo_neto'] for d in flujo_data]
        }
