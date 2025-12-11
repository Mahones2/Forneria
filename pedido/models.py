from django.db import models
from pos.models import Producto # 🚨 CORRECCIÓN: Importar Producto desde la app 'pos'

ESTADOS_PEDIDO = (
    ('Pendiente', 'Pendiente de Procesar'),
    ('En Proceso', 'En Proceso (Cocina/Preparación)'),
    ('Enviado', 'Enviado/En Camino'),
    ('Completado', 'Completado'),
    ('Cancelado', 'Cancelado'),
)

class Pedido(models.Model):
    """Representa una orden de venta o pedido."""
    
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS_PEDIDO, default='Pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Relación opcional con Cliente (Si existe el modelo Cliente en pos.models)
    # cliente = models.ForeignKey('pos.Cliente', on_delete=models.SET_NULL, null=True, blank=True)
    cliente_nombre = models.CharField(max_length=100, blank=True, null=True)
    
    ubicacion = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Pedido #{self.id} - {self.estado}"

class DetallePedido(models.Model):
    """Representa un ítem dentro de un pedido."""
    
    pedido = models.ForeignKey(Pedido, related_name='detalles', on_delete=models.CASCADE)
    
    
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2) 
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False) 

    def save(self, *args, **kwargs):
        # Calcula el subtotal automáticamente
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en Pedido #{self.pedido.id}"