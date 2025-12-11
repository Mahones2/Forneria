from rest_framework import serializers
from .models import Pedido, DetallePedido

class DetallePedidoSerializer(serializers.ModelSerializer):
    """Serializador para el detalle (ítems) de un pedido."""
    
    # Muestra el nombre del producto (asumiendo que Producto tiene campo 'nombre')
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre') 

    class Meta:
        model = DetallePedido
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal']
        read_only_fields = ['subtotal']

class PedidoSerializer(serializers.ModelSerializer):
    """Serializador principal para el modelo Pedido."""
    
    # Campo anidado para manejar los ítems del pedido
    detalles = DetallePedidoSerializer(many=True)
    
    class Meta:
        model = Pedido
        fields = [
            'id', 'total', 'estado', 'fecha_creacion', 'fecha_actualizacion',
            'cliente_nombre', 'ubicacion', 'detalles'
        ]
        read_only_fields = ['total', 'fecha_creacion', 'fecha_actualizacion']

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        pedido = Pedido.objects.create(**validated_data)
        
        total_pedido = 0
        
        for detalle_data in detalles_data:
            detalle = DetallePedido.objects.create(pedido=pedido, **detalle_data)
            total_pedido += detalle.subtotal

        pedido.total = total_pedido
        pedido.save()

        return pedido