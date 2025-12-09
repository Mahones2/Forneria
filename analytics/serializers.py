"""
Serializers para Analytics
Como trabajamos con datos agregados (dicts), usamos serializers simples
"""
from rest_framework import serializers


class ResumenPeriodoSerializer(serializers.Serializer):
    """Serializer para resumen de periodo"""
    total_ventas = serializers.DecimalField(max_digits=12, decimal_places=2)
    cantidad_transacciones = serializers.IntegerField()
    ticket_promedio = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_sin_iva = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_iva = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_descuentos = serializers.DecimalField(max_digits=12, decimal_places=2)
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()


class VentasDiariasSerializer(serializers.Serializer):
    """Serializer para ventas diarias (Chart.js format)"""
    labels = serializers.ListField(child=serializers.CharField())
    totales = serializers.ListField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    cantidades = serializers.ListField(child=serializers.IntegerField())


class ProductoTopSerializer(serializers.Serializer):
    """Serializer para productos top"""
    producto_id = serializers.IntegerField()
    nombre = serializers.CharField()
    categoria = serializers.CharField(allow_null=True)
    cantidad_vendida = serializers.IntegerField()
    ingresos = serializers.DecimalField(max_digits=12, decimal_places=2)
    transacciones = serializers.IntegerField()


class VentasPorCategoriaSerializer(serializers.Serializer):
    """Serializer para ventas por categoría"""
    labels = serializers.ListField(child=serializers.CharField())
    totales = serializers.ListField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    cantidades = serializers.ListField(child=serializers.IntegerField())


class VentasPorCanalSerializer(serializers.Serializer):
    """Serializer para ventas por canal"""
    canal = serializers.CharField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    cantidad = serializers.IntegerField()
    ticket_promedio = serializers.DecimalField(max_digits=10, decimal_places=2)


class ClienteTopSerializer(serializers.Serializer):
    """Serializer para clientes top"""
    cliente_id = serializers.IntegerField()
    nombre = serializers.CharField()
    rut = serializers.CharField()
    total_compras = serializers.DecimalField(max_digits=12, decimal_places=2)
    num_compras = serializers.IntegerField()
    ticket_promedio = serializers.DecimalField(max_digits=10, decimal_places=2)


class KPIsHoySerializer(serializers.Serializer):
    """Serializer para KPIs del día"""
    hoy = serializers.DictField()
    ayer = serializers.DictField()
    variacion_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
