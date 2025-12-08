from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from decimal import Decimal

# ==========================================
# 1. PARAMÉTRICAS Y ACTORES GLOBALES
# ==========================================

class Ubicacion(models.Model):
    """
    Normalización: Lugar físico en bodega/almacén.
    Se usa tanto para Insumos como para Lotes de Productos.
    """
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return self.nombre

class Proveedor(models.Model):
    """Datos maestros de proveedores para compras"""
    nombre = models.CharField(max_length=150)
    contacto = models.CharField(max_length=150, null=True, blank=True)
    correo = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    direccion = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=150)
    correo = models.CharField(max_length=100, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    es_empresa = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

class Direccion(models.Model):
    """Para delivery múltiple (Casa, Oficina)"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='direcciones')
    alias = models.CharField(max_length=50, help_text="Ej: Casa, Oficina")
    calle = models.CharField(max_length=200)
    numero = models.CharField(max_length=20)
    comuna = models.CharField(max_length=100)
    referencia = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.calle} {self.numero}, {self.comuna}"

class Empleado(models.Model):
    CARGO_CHOICES = [
        ('Administrador', 'Administrador'),
        ('Vendedor', 'Vendedor'),
    ]

    run = models.CharField(max_length=45, unique=True)
    fono = models.CharField(max_length=20, unique=True)
    direccion = models.CharField(max_length=200)
    
    cargo = models.CharField(
        max_length=15, 
        choices=CARGO_CHOICES,
        default='Vendedor'
    )
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} ({self.get_cargo_display()})"

class Turno(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='turnos')
    fecha = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField(null=True, blank=True)
    monto_inicial_caja = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_final_caja = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Turno de {self.empleado} el {self.fecha}"

# ==========================================
# 2. ABASTECIMIENTO (MATERIAS PRIMAS)
# ==========================================

class Insumo(models.Model):
    """Materia prima (Harina, Envases, etc.) que NO se vende directamente"""
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    unidad_medida = models.CharField(max_length=50, null=True, blank=True, help_text="kg, litros, unidades")
    stock_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Relaciones
    proveedor_preferido = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='insumos')
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='insumos')

    def __str__(self):
        return self.nombre

class OrdenCompra(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    ]
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='ordenes')
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    # Se recomienda recalcular el total antes de guardar
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"OC-{self.id} {self.proveedor.nombre}"

    def actualizar_total(self):
        total_calculado = sum(item.subtotal() for item in self.items.all())
        self.total = total_calculado
        self.save(update_fields=['total'])

class OrdenCompraItem(models.Model):
    orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='items')
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

# ==========================================
# 3. CATÁLOGO Y PRODUCTOS (PRODUCTO TERMINADO)
# ==========================================

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    codigo_barra = models.CharField(max_length=50, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=300, null=True, blank=True)
    marca = models.CharField(max_length=100, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio Neto o Bruto según tu lógica")
    tipo = models.CharField(max_length=100, null=True, blank=True)
    presentacion = models.CharField(max_length=100, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    
    imagen_referencial = models.ImageField(
        upload_to='productos_imagenes/',
        null=True,
        blank=True,
        help_text="Imagen principal de referencia del producto."
    )

    # OPTIMIZACIÓN DE RENDIMIENTO (Denormalización controlada por signals)
    stock_fisico = models.IntegerField(default=0, db_index=True) 
    stock_minimo_global = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock_fisico})"

    def precio_con_iva(self, iva=Decimal('0.19')):
        return self.precio_venta * (1 + iva)

class Nutricional(models.Model):
    calorias = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proteinas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    grasas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbohidratos = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    azucares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sodio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name="nutricional")

# ==========================================
# 4. INVENTARIO PRODUCTOS (LOTES Y TRAZABILIDAD)
# ==========================================

class Lote(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="lotes")
    numero_lote = models.CharField(max_length=50, null=True, blank=True)
    fecha_elaboracion = models.DateField(null=True, blank=True)
    fecha_caducidad = models.DateField()
    
    # CRÍTICO PARA REPORTES FINANCIEROS
    precio_costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo de producción o compra")
    
    stock_inicial = models.IntegerField()
    stock_actual = models.IntegerField(default=0)
    
    # Integración con Ubicación
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes')
    
    creado = models.DateTimeField(auto_now_add=True)
    eliminado = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['fecha_caducidad'] # FIFO: Primero vence, primero sale

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.producto.nombre}"

    @property
    def esta_vencido(self):
        return self.fecha_caducidad < timezone.now().date()
    
    def save(self, *args, **kwargs):
        if self._state.adding and self.stock_actual == 0:
            # Si es un lote nuevo y no se ha definido stock_actual,
            # inicialízalo con stock_inicial
            self.stock_actual = self.stock_inicial
        super().save(*args, **kwargs)

class MovimientoInventario(models.Model):
    """Kardex: La verdad contable de cada entrada/salida de Productos"""
    TIPO_CHOICES = [('entrada', 'Entrada'), ('salida', 'Salida (Venta)'), ('merma', 'Merma/Ajuste')]
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    cantidad = models.IntegerField() # Positivo entrada, Negativo salida
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    
    referencia = models.CharField(max_length=100, help_text="ID Venta o Nro Factura Proveedor")
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

class Alerta(models.Model):
    TIPO_CHOICES = [('stock_bajo', 'Stock Bajo'), ('vencimiento', 'Próximo a Vencer')]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    mensaje = models.CharField(max_length=255)
    
    # Corregido: unificado a un solo campo producto y lote
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True)
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    resuelto = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.tipo}: {self.mensaje}"

# ==========================================
# 5. E-COMMERCE Y VENTAS
# ==========================================

class Carrito(models.Model):
    """Temporal, antes de convertirse en Venta"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True) 
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    
    def subtotal(self):
        return self.producto.precio_venta * self.cantidad

class Venta(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Pago'),
        ('pagado', 'Pagado / En Preparación'),
        ('en_camino', 'En Camino'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    CANAL_CHOICES = [('pos', 'Punto de Venta'), ('web', 'E-commerce')]
    DOC_CHOICES = [('boleta', 'Boleta'), ('factura', 'Factura')]

    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Logística
    canal_venta = models.CharField(max_length=10, choices=CANAL_CHOICES, default='pos')
    direccion_despacho = models.ForeignKey(Direccion, on_delete=models.SET_NULL, null=True, blank=True)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Totales (Denormalización necesaria para histórico contable)
    neto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Estado y Documento
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    tipo_documento = models.CharField(max_length=20, choices=DOC_CHOICES, default='boleta')
    folio_documento = models.CharField(max_length=50, null=True, blank=True, help_text="Folio SII")

    def __str__(self):
        return f"Venta #{self.id} - Total: {self.total}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    # Precio histórico (si el producto sube de precio mañana, esta venta no cambia)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) 
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def subtotal(self):
        return (self.cantidad * self.precio_unitario) - self.descuento

class Pago(models.Model):
    METODO_CHOICES = [('EFE', 'Efectivo'), ('DEB', 'Débito'), ('CRE', 'Crédito'), ('TRA', 'Transferencia')]
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto APLICADO a la venta.")
    metodo = models.CharField(max_length=3, choices=METODO_CHOICES)
    referencia_externa = models.CharField(max_length=100, null=True, blank=True, help_text="ID Transbank/Stripe")
    fecha = models.DateTimeField(auto_now_add=True)
    
    # 1. Monto físico entregado por el cliente
    monto_recibido = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        help_text="Monto total entregado por el cliente (solo en efectivo)."
    )
    
    # 2. CAMPO PARA ALMACENAR EL VUELTO
    vuelto = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        help_text="Vuelto entregado al cliente (solo en efectivo)."
    )

    def save(self, *args, **kwargs):
        # Aseguramos que los valores sean Decimal para operar
        monto_recibido_dec = self.monto_recibido if self.monto_recibido is not None else Decimal(0)
        monto_aplicado_dec = self.monto if self.monto is not None else Decimal(0)
        
        # Lógica de cálculo solo si es pago en efectivo
        if self.metodo == 'EFE':
            
            diferencia = monto_recibido_dec - monto_aplicado_dec
            
            # Si la diferencia es positiva, es el vuelto. Si es cero o negativa, el vuelto es 0.
            self.vuelto = diferencia if diferencia > 0 else Decimal(0)
        else:
            # Para pagos electrónicos (Débito, Crédito, Transf.), el vuelto siempre es cero.
            self.vuelto = Decimal(0)
            
        super().save(*args, **kwargs)

# ==========================================
# 6. LÓGICA AUTOMÁTICA (SIGNALS)
# ==========================================

# 6.1 Actualización de Stock de Producto Terminado (Lotes)
@receiver(post_save, sender=Lote)
# Desconectamos post_save de MovimientoInventario temporalmente,
# o lo usamos SOLO para recalcular.
@receiver(post_save, sender=MovimientoInventario) 
def actualizar_stock_producto(sender, instance, created, **kwargs):

    # --- Paso 1: IGNORAR MovimientoInventario si el servicio ya lo manejó ---
    # Si la lógica de MovimientoInventario es compleja, es mejor no tocar el Lote aquí.
    # Eliminamos el bloque del "Paso 1" que causaba la doble actualización/suma invertida.
    
    # Si el sender es MovimientoInventario, el producto es instance.producto
    # Si el sender es Lote, el producto es instance.producto
    
    if sender.__name__ == "MovimientoInventario":
        producto = instance.producto
    elif sender.__name__ == "Lote":
        producto = instance.producto
    else:
        return
        
    # --- Paso 2: recalcular stock del producto (Esta parte es la que funciona) ---
    total = Lote.objects.filter(producto=producto, eliminado__isnull=True).aggregate(
        total=Sum('stock_actual')
    )['total'] or 0

    if producto.stock_fisico != total:
        producto.stock_fisico = total
        producto.save(update_fields=['stock_fisico'])

# 6.2 Actualización de Stock de Insumos (Orden de Compra)
@receiver(pre_save, sender=OrdenCompra)
def procesar_recepcion_orden_compra(sender, instance, **kwargs):
    """
    Si una Orden de Compra cambia a estado 'recibida', sumar stock a los insumos.
    Nota: Esto requiere manejo cuidadoso para no sumar doble si se guarda 2 veces.
    Una mejor práctica es usar una acción de admin o servicio dedicado, pero aquí se usa signal para automatización básica.
    """
    if instance.pk: # Si ya existe (es una actualización)
        try:
            orden_anterior = OrdenCompra.objects.get(pk=instance.pk)
            # Solo si cambia de no-recibida a recibida
            if orden_anterior.estado != 'recibida' and instance.estado == 'recibida':
                for item in instance.items.all():
                    insumo = item.insumo
                    insumo.stock_actual = F('stock_actual') + item.cantidad
                    insumo.save()
        except OrdenCompra.DoesNotExist:
            pass

# 6.3 Cálculo automático de subtotales en OC Items
@receiver(post_save, sender=OrdenCompraItem)
def actualizar_total_orden_compra(sender, instance, **kwargs):
    """Actualiza el total de la orden cuando se agrega un item"""
    instance.orden.actualizar_total()