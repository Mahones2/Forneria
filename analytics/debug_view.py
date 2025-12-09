"""
Vista de debug temporal para verificar datos
"""
from django.http import JsonResponse
from django.utils import timezone
from .services import FinanzasMetrics

def debug_datos(request):
    """Vista de debug para verificar que los datos se obtienen correctamente"""

    try:
        kpis = FinanzasMetrics.kpis_hoy()
        resumen = FinanzasMetrics.resumen_periodo()
        metricas_avanzadas = FinanzasMetrics.metricas_avanzadas()
        ventas_diarias = FinanzasMetrics.ventas_diarias()

        return JsonResponse({
            'status': 'OK',
            'kpis': kpis,
            'resumen': resumen,
            'metricas_avanzadas': metricas_avanzadas,
            'ventas_diarias': ventas_diarias,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'ERROR',
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)
