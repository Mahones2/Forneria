"""
URLs para Analytics API
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Dashboard HTML
    path('dashboard/', views.dashboard_finanzas, name='dashboard-finanzas'),

    # Debug temporal
    path('debug/', lambda request: __import__('django.http').JsonResponse({
        'kpis': __import__('analytics.services', fromlist=['FinanzasMetrics']).FinanzasMetrics.kpis_hoy(),
        'resumen': __import__('analytics.services', fromlist=['FinanzasMetrics']).FinanzasMetrics.resumen_periodo()
    }), name='debug'),

    # Finanzas - Endpoints principales
    path('finanzas/resumen/', views.resumen_financiero, name='finanzas-resumen'),
    path('finanzas/kpis-hoy/', views.kpis_hoy, name='finanzas-kpis-hoy'),

    # Finanzas - Gráficos temporales
    path('finanzas/ventas-diarias/', views.ventas_diarias, name='finanzas-ventas-diarias'),
    path('finanzas/ventas-por-hora/', views.ventas_por_hora, name='finanzas-ventas-por-hora'),
    path('finanzas/comparativa-mensual/', views.comparativa_mensual, name='finanzas-comparativa-mensual'),

    # Finanzas - Análisis de productos
    path('finanzas/productos-top/', views.productos_top, name='finanzas-productos-top'),
    path('finanzas/ventas-por-categoria/', views.ventas_por_categoria, name='finanzas-ventas-por-categoria'),

    # Finanzas - Otros análisis
    path('finanzas/ventas-por-canal/', views.ventas_por_canal, name='finanzas-ventas-por-canal'),
    path('finanzas/clientes-top/', views.clientes_top, name='finanzas-clientes-top'),

    # === ENDPOINTS AVANZADOS ===
    # Métricas avanzadas
    path('finanzas/metricas-avanzadas/', views.metricas_avanzadas, name='metricas-avanzadas'),
    path('finanzas/ticket-segmentado/', views.ticket_promedio_segmentado, name='ticket-segmentado'),
    path('finanzas/ventas-dia-semana/', views.ventas_por_dia_semana, name='ventas-dia-semana'),
    path('finanzas/clientes-nuevos-recurrentes/', views.clientes_nuevos_vs_recurrentes, name='clientes-nuevos'),
    path('finanzas/heatmap-ventas/', views.heatmap_ventas, name='heatmap-ventas'),
    path('finanzas/proyeccion/', views.proyeccion_ventas, name='proyeccion-ventas'),
    path('finanzas/mom/', views.comparativa_mom, name='comparativa-mom'),
    path('finanzas/alertas/', views.alertas_automaticas, name='alertas-automaticas'),

    # Exportación
    path('finanzas/exportar/excel/', views.exportar_excel, name='exportar-excel'),
    path('finanzas/exportar/csv/', views.exportar_csv, name='exportar-csv'),
    path('finanzas/exportar/pdf/', views.exportar_pdf, name='exportar-pdf'),
]
