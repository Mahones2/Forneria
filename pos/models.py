from django.db import models
from django.db.models import F, Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from decimal import Decimal, ROUND_HALF_UP # Necesario para cálculos de precisión
from datetime import date # Necesario para cálculos de fecha en Lote
from django.utils import timezone
import os
import unicodedata
from django.utils.text import slugify
# ==========================================
# 1. MAESTROS
# ==========================================

class Ubicacion(models.Model):
    """Lugar físico en bodega/almacén."""
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
    
    # Asumo que el modelo User está disponible.
    # Si Empleado hereda de User, esto debe ajustarse.
    usuario = models.OneToOneField(User, on_delete=models.CASCADE) 

    def __str__(self):
        # Necesita que el usuario tenga first_name y last_name
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
# 2. ABASTECIMIENTO (MATERIAS PRIMAS) - Sin cambios
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
# 3. CATÁLOGO Y PRODUCTOS (PRODUCTO TERMINADO) - MEJORADO
# ==========================================

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.nombre


def renombrar_imagen(instance, filename):
    # Extraer extensión
    extension = filename.split('.')[-1]

    # Convertir nombre del producto a formato seguro
    nombre_producto = slugify(instance.nombre)

    # Contador basado en ID (si no existe aún, usar timestamp)
    if instance.id:
        contador = f"{instance.id:03d}"
    else:
        from time import time
        contador = str(int(time()))

    # Crear nombre final
    nuevo_nombre = f"{nombre_producto}_{contador}.{extension}"

    return os.path.join('productos_imagenes', nuevo_nombre)



class Producto(models.Model):
    codigo_barra = models.CharField(max_length=50, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=300, null=True, blank=True)
    marca = models.CharField(max_length=100, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio Neto o Bruto según tu lógica")
    
    # NUEVO CAMPO: Costo Promedio para el Dashboard
    costo_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Costo promedio o actual del producto para análisis de rentabilidad"
    )
    
    tipo = models.CharField(max_length=100, null=True, blank=True)
    presentacion = models.CharField(max_length=100, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    
    imagen_referencial = models.ImageField(
        upload_to=renombrar_imagen,
        null=True,
        blank=True
    )



    # OPTIMIZACIÓN DE RENDIMIENTO (Denormalización controlada por signals)
    stock_fisico = models.IntegerField(default=0, db_index=True) 
    stock_minimo_global = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock_fisico})"

    def precio_con_iva(self, iva=Decimal('0.19')):
        # Usamos Decimal para mantener la precisión
        precio = self.precio_venta if self.precio_venta is not None else Decimal('0')
        result = (precio * (Decimal(1) + iva)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return result
        
    def stock_total(self):
        """Suma el stock_actual de todos los lotes asociados (usado para verificación)."""
        return sum(lote.stock_actual or 0 for lote in self.lotes.all())

class Nutricional(models.Model):
    calorias = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proteinas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    grasas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbohidratos = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    azucares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sodio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name="nutricional")

# ==========================================
# 4. INVENTARIO PRODUCTOS (LOTES Y TRAZABILIDAD) - MEJORADO
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
    
    # Integración con Ubicación (Modelo 1 original)
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
    
    def dias_para_caducar(self):
        """Días (enteros) hasta la caducidad. Negativo si ya está vencido."""
        if not self.fecha_caducidad:
            return None
        delta = self.fecha_caducidad - date.today()
        return delta.days
        
    def agregar_stock(self, cantidad):
        """Agrega stock al lote y lo persiste."""
        if cantidad is None or cantidad <= 0:
            raise ValueError("La cantidad a agregar debe ser mayor a 0")
        self.stock_actual = (self.stock_actual or 0) + int(cantidad)
        self.save(update_fields=["stock_actual"])
        return self.stock_actual

    def retirar_stock(self, cantidad):
        """Resta stock del lote si hay suficiente; lanza ValueError si no."""
        if cantidad is None or cantidad <= 0:
            raise ValueError("La cantidad a retirar debe ser mayor a 0")
        if (self.stock_actual or 0) < cantidad:
            raise ValueError("Stock insuficiente en el lote")
        self.stock_actual = int(self.stock_actual) - int(cantidad)
        self.save(update_fields=["stock_actual"])
        return self.stock_actual

    def save(self, *args, **kwargs):
        if self._state.adding and self.stock_actual == 0:
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
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True)
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    resuelto = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.tipo}: {self.mensaje}"

# ==========================================
# 5. E-COMMERCE Y VENTAS - MEJORADO
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
    fecha_entrega = models.DateField(null=True, blank=True)
    
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
        
    def calcular_subtotal(self):
        """Suma cantidad * precio_unitario (sin considerar descuentos) de los detalles."""
        # Aseguramos la suma como Decimal para precisión
        subtotal = sum((d.cantidad * d.precio_unitario) for d in self.detalles.all())
        return subtotal

    def calcular_total_descuento(self):
        """Suma todos los descuentos aplicados en los detalles."""
        return sum(d.descuento for d in self.detalles.all())

    def calcular_totales_desde_detalles(self, iva_rate=Decimal('0.19')):
        """Calcula y actualiza los totales de la venta basados en sus detalles."""
        subtotal = self.calcular_subtotal()
        descuento = self.calcular_total_descuento()
        
        neto_bruto = subtotal - descuento
        neto = neto_bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        iva = (neto * iva_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = (neto + iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        self.neto = neto
        self.iva = iva
        self.total = total
        self.save(update_fields=["neto", "iva", "total"])
        return {
            "neto": neto,
            "iva": iva,
            "total": total,
            "descuento": descuento
        }

    def actualizar_stock(self, usuario):
        """
        Actualiza el stock de los productos restando las cantidades vendidas, 
        consumiendo lotes por fecha de caducidad ascendente (FIFO).
        """
        for detalle in self.detalles.all():
            producto = detalle.producto
            cantidad = detalle.cantidad
            
            # Consumir lotes por fecha de caducidad (próxima a vencer primero)
            lotes = producto.lotes.filter(stock_actual__gt=0, eliminado__isnull=True).order_by('fecha_caducidad')
            restante = int(cantidad)
            
            if restante > producto.stock_fisico:
                 raise ValueError(f"Stock total insuficiente para producto {producto.nombre}: falta {restante}")
                 
            for lote in lotes:
                if restante <= 0:
                    break
                
                disponible = lote.stock_actual or 0
                to_retirar = min(disponible, restante)
                
                if to_retirar > 0:
                    # Usamos el método seguro de Lote
                    lote.retirar_stock(to_retirar) 
                    
                    # Crear movimiento de salida (Kardex)
                    MovimientoInventario.objects.create(
                        tipo='salida',
                        cantidad=-to_retirar, # Negativo para indicar salida
                        lote=lote,
                        producto=producto,
                        referencia=f"Venta #{self.id}",
                        usuario=usuario # El usuario que realiza la venta
                    )
                    restante -= to_retirar
            
            if restante > 0:
                # Esto no debería pasar si la verificación inicial es correcta, pero es un seguro.
                raise ValueError(f"Error interno: No se pudo retirar todo el stock para {producto.nombre}")

    # =========================================================================
    # METODOS HELPER (Estaban en tu primer código pero faltaban en el segundo)
    # =========================================================================

    def marcar_como_pagado(self):
        """Mueve el pedido a cocina/preparación"""
        self.estado = 'pagado'
        self.save(update_fields=['estado'])

    def marcar_en_camino(self):
        """El pedido salió a reparto"""
        if not self.direccion_despacho:
            raise ValueError("No se puede despachar sin dirección")
        self.estado = 'en_camino'
        self.save(update_fields=['estado'])

    def marcar_entregado(self):
        """Pedido finalizado"""
        self.estado = 'entregado'
        self.save(update_fields=['estado'])


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    # Precio histórico (si el producto sube de precio mañana, esta venta no cambia)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) 
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def subtotal(self):
        return (self.cantidad * self.precio_unitario) - self.descuento

class GastoOperativo(models.Model):
    """Modelo para registrar gastos fijos o variables no relacionados con insumos."""
    nombre = models.CharField(max_length=150)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)
    descripcion = models.CharField(max_length=250, null=True, blank=True)
    
    # Opcional: Relacionar con Categoría de Gastos si tienes una.
    # categoria_gasto = models.ForeignKey(CategoriaGasto, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.nombre} - ${self.monto}"

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
# 6. LÓGICA AUTOMÁTICA (SIGNALS) - AJUSTADA
# ==========================================

# 6.1 Actualización de Stock de Producto Terminado (Lotes)
# SOLO se activa cuando un Lote cambia (Lote.save() llama esto).
# MovimientoInventario ya NO activa este signal para evitar duplicidades
@receiver(post_save, sender=Lote)
def actualizar_stock_producto(sender, instance, **kwargs):

    producto = instance.producto
        
    # Recalcular stock_fisico sumando stock_actual de todos los lotes activos
    total = Lote.objects.filter(producto=producto, eliminado__isnull=True).aggregate(
        total=Sum('stock_actual')
    )['total'] or 0

    if producto.stock_fisico != total:
        producto.stock_fisico = total
        producto.save(update_fields=['stock_fisico'])

# 6.2 Actualización de Stock de Insumos (Orden de Compra) - Sin cambios
@receiver(pre_save, sender=OrdenCompra)
def procesar_recepcion_orden_compra(sender, instance, **kwargs):
    """
    Si una Orden de Compra cambia a estado 'recibida', sumar stock a los insumos.
    """
    if instance.pk: 
        try:
            orden_anterior = OrdenCompra.objects.get(pk=instance.pk)
            # Solo si cambia de no-recibida a recibida
            if orden_anterior.estado != 'recibida' and instance.estado == 'recibida':
                for item in instance.items.all():
                    insumo = item.insumo
                    # Nota: F() es mejor para evitar condiciones de carrera, pero requiere post-save en Insumo
                    insumo.stock_actual = F('stock_actual') + item.cantidad 
                    insumo.save()
        except OrdenCompra.DoesNotExist:
            pass

# 6.3 Cálculo automático de subtotales en OC Items - Sin cambios
@receiver(post_save, sender=OrdenCompraItem)
def actualizar_total_orden_compra(sender, instance, **kwargs):
    """Actualiza el total de la orden cuando se agrega un item"""
    instance.orden.actualizar_total()
