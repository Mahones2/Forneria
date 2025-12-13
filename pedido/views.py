from rest_framework import viewsets, permissions
from .models import Pedido
from .serializers import PedidoSerializer

class PedidoViewSet(viewsets.ModelViewSet):
    """ViewSet para listar, crear, recuperar, actualizar y eliminar Pedidos."""
    
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer
    
    # Usar el permiso de autenticación que estés usando en tu API
    permission_classes = [permissions.AllowAny] 

    def get_queryset(self):
        # Opcional: Filtra solo los pedidos 'activos' (los que no son Completado/Cancelado)
        # Esto replicaría el filtro que usamos en el frontend
        if self.action == 'list':
            return self.queryset.exclude(estado__in=['Completado', 'Cancelado'])
        return self.queryset