from django.db import models
from django.db.models import F, Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError # Importante para validaciones
from decimal import Decimal, ROUND_HALF_UP 
from datetime import date 
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

    def clean(self):
        """Validaciones a nivel de modelo (Aporte de tu compañera)"""
        import re
        if self.rut:
            # Valida que el RUT tenga formato X.XXX.XXX-X o parecidos
            rut_pattern = r'^(\d{1,2}\.?\d{3}\.?\d{3})-[\dkK]$'
            if not re.match(rut_pattern, self.rut):
                raise ValidationError({
                    'rut': 'Formato RUT inválido. Use XX.XXX.XXX-X o XXXXXXXX-X'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    unidad_medida = models.CharField(max_length=50, null=True, blank=True, help_text="kg, litros, unidades")
    stock_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
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
# 3. CATÁLOGO Y PRODUCTOS
# ==========================================

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.nombre

def renombrar_imagen(instance, filename):
    extension = filename.split('.')[-1]
    nombre_producto = slugify(instance.nombre)
    if instance.id:
        contador = f"{instance.id:03d}"
    else:
        from time import time
        contador = str(int(time()))
    nuevo_nombre = f"{nombre_producto}_{contador}.{extension}"
    return os.path.join('productos_imagenes', nuevo_nombre)

class Etiqueta(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.nombre

class Producto(models.Model):
    # ... tus otros campos existentes ...
    codigo_barra = models.CharField(max_length=50, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=300, null=True, blank=True)
    marca = models.CharField(max_length=100, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    
    costo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        help_text="Costo promedio o actual del producto para análisis de rentabilidad"
    )
    
    tipo = models.CharField(max_length=100, null=True, blank=True)
    presentacion = models.CharField(max_length=100, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    
    # La imagen se sube a Cloudinary y se guarda solo la URL
    imagen_url = models.URLField(max_length=500, null=True, blank=True, help_text="URL de la imagen en Cloudinary")

    stock_fisico = models.IntegerField(default=0, db_index=True) 
    stock_minimo_global = models.IntegerField(default=5)

    # === AQUÍ AGREGAMOS LA RELACIÓN ===
    # blank=True permite guardar un producto sin etiquetas
    # related_name='productos' permite buscar Etiqueta.productos.all()
    etiquetas = models.ManyToManyField(Etiqueta, blank=True, related_name='productos')

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock_fisico})"

    # ... tus métodos precio_con_iva, stock_total, clean y save se mantienen IGUAL ...
    def precio_con_iva(self, iva=Decimal('0.19')):
        precio = self.precio_venta if self.precio_venta is not None else Decimal('0')
        result = (precio * (Decimal(1) + iva)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return result

    def stock_total(self):
        return sum(lote.stock_actual or 0 for lote in self.lotes.all())

    def clean(self):
        if self.precio_venta is not None and self.precio_venta < 0:
            raise ValidationError({'precio_venta': 'El precio de venta no puede ser negativo'})
        if self.costo_unitario is not None and self.costo_unitario < 0:
            raise ValidationError({'costo_unitario': 'El costo unitario no puede ser negativo'})
        if self.stock_minimo_global is not None and self.stock_minimo_global < 0:
            raise ValidationError({'stock_minimo_global': 'El stock mínimo no puede ser negativo'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Nutricional(models.Model):
    calorias = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proteinas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    grasas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbohidratos = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    azucares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sodio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name="nutricional")

# ==========================================
# 4. INVENTARIO PRODUCTOS (LOTES)
# ==========================================

class Lote(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="lotes")
    numero_lote = models.CharField(max_length=50, null=True, blank=True)
    fecha_elaboracion = models.DateField(null=True, blank=True)
    fecha_caducidad = models.DateField()
    precio_costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_inicial = models.IntegerField()
    stock_actual = models.IntegerField(default=0)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes')
    creado = models.DateTimeField(auto_now_add=True)
    eliminado = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['fecha_caducidad'] 

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.producto.nombre}"

    @property
    def esta_vencido(self):
        return self.fecha_caducidad < timezone.now().date()
    
    def dias_para_caducar(self):
        if not self.fecha_caducidad:
            return None
        delta = self.fecha_caducidad - date.today()
        return delta.days
        
    def agregar_stock(self, cantidad):
        if cantidad is None or cantidad <= 0:
            raise ValueError("La cantidad a agregar debe ser mayor a 0")
        self.stock_actual = (self.stock_actual or 0) + int(cantidad)
        self.save(update_fields=["stock_actual"])
        return self.stock_actual

    def retirar_stock(self, cantidad):
        if cantidad is None or cantidad <= 0:
            raise ValueError("La cantidad a retirar debe ser mayor a 0")
        if (self.stock_actual or 0) < cantidad:
            raise ValueError("Stock insuficiente en el lote")
        self.stock_actual = int(self.stock_actual) - int(cantidad)
        self.save(update_fields=["stock_actual"])
        return self.stock_actual

    def clean(self):
        """Validaciones (Aporte de tu compañera)"""
        if self.fecha_elaboracion and self.fecha_caducidad:
            if self.fecha_caducidad <= self.fecha_elaboracion:
                raise ValidationError({'fecha_caducidad': 'La caducidad debe ser posterior a la elaboración'})
        if self.precio_costo_unitario is not None and self.precio_costo_unitario < 0:
            raise ValidationError({'precio_costo_unitario': 'El costo no puede ser negativo'})
        if self.stock_inicial is not None and self.stock_inicial < 0:
             raise ValidationError({'stock_inicial': 'Stock no puede ser negativo'})

    def save(self, *args, **kwargs):
        if 'update_fields' not in kwargs or kwargs['update_fields'] is None:
            self.full_clean()
        if self._state.adding and self.stock_actual == 0:
            self.stock_actual = self.stock_inicial
        super().save(*args, **kwargs)

class MovimientoInventario(models.Model):
    TIPO_CHOICES = [('entrada', 'Entrada'), ('salida', 'Salida (Venta)'), ('merma', 'Merma/Ajuste')]
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    cantidad = models.IntegerField() 
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    referencia = models.CharField(max_length=100)
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
# 5. E-COMMERCE Y VENTAS
# ==========================================

class Carrito(models.Model):
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
    
    # Totales
    neto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    tipo_documento = models.CharField(max_length=20, choices=DOC_CHOICES, default='boleta')
    folio_documento = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Venta #{self.id} - Total: {self.total}"
        
    def calcular_subtotal(self):
        subtotal = sum((d.cantidad * d.precio_unitario) for d in self.detalles.all())
        return subtotal

    def calcular_total_descuento(self):
        return sum(d.descuento for d in self.detalles.all())

    def calcular_totales_desde_detalles(self, iva_rate=Decimal('0.19')):
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
        return {"neto": neto, "iva": iva, "total": total, "descuento": descuento}

    def actualizar_stock(self, usuario):
        for detalle in self.detalles.all():
            producto = detalle.producto
            cantidad = detalle.cantidad
            lotes = producto.lotes.filter(stock_actual__gt=0, eliminado__isnull=True).order_by('fecha_caducidad')
            restante = int(cantidad)
            
            if restante > producto.stock_fisico:
                 raise ValueError(f"Stock total insuficiente para producto {producto.nombre}: falta {restante}")
                 
            for lote in lotes:
                if restante <= 0: break
                disponible = lote.stock_actual or 0
                to_retirar = min(disponible, restante)
                if to_retirar > 0:
                    lote.retirar_stock(to_retirar) 
                    MovimientoInventario.objects.create(
                        tipo='salida',
                        cantidad=-to_retirar,
                        lote=lote,
                        producto=producto,
                        referencia=f"Venta #{self.id}",
                        usuario=usuario
                    )
                    restante -= to_retirar
            
            if restante > 0:
                raise ValueError(f"Error interno: No se pudo retirar todo el stock para {producto.nombre}")

    # =========================================================================
    # METODOS HELPER
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
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) 
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def subtotal(self):
        return (self.cantidad * self.precio_unitario) - self.descuento

class GastoOperativo(models.Model):
    nombre = models.CharField(max_length=150)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)
    descripcion = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - ${self.monto}"

class Pago(models.Model):
    METODO_CHOICES = [('EFE', 'Efectivo'), ('DEB', 'Débito'), ('CRE', 'Crédito'), ('TRA', 'Transferencia')]
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto APLICADO a la venta.")
    metodo = models.CharField(max_length=3, choices=METODO_CHOICES)
    referencia_externa = models.CharField(max_length=100, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    monto_recibido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vuelto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        monto_recibido_dec = self.monto_recibido if self.monto_recibido is not None else Decimal(0)
        monto_aplicado_dec = self.monto if self.monto is not None else Decimal(0)
        if self.metodo == 'EFE':
            diferencia = monto_recibido_dec - monto_aplicado_dec
            self.vuelto = diferencia if diferencia > 0 else Decimal(0)
        else:
            self.vuelto = Decimal(0)
        super().save(*args, **kwargs)

# ==========================================
# 6. SIGNALS
# ==========================================

@receiver(post_save, sender=Lote)
def actualizar_stock_producto(sender, instance, **kwargs):
    producto = instance.producto
    total = Lote.objects.filter(producto=producto, eliminado__isnull=True).aggregate(
        total=Sum('stock_actual')
    )['total'] or 0
    if producto.stock_fisico != total:
        producto.stock_fisico = total
        producto.save(update_fields=['stock_fisico'])

@receiver(pre_save, sender=OrdenCompra)
def procesar_recepcion_orden_compra(sender, instance, **kwargs):
    if instance.pk: 
        try:
            orden_anterior = OrdenCompra.objects.get(pk=instance.pk)
            if orden_anterior.estado != 'recibida' and instance.estado == 'recibida':
                for item in instance.items.all():
                    insumo = item.insumo
                    insumo.stock_actual = F('stock_actual') + item.cantidad 
                    insumo.save()
        except OrdenCompra.DoesNotExist:
            pass

@receiver(post_save, sender=OrdenCompraItem)
def actualizar_total_orden_compra(sender, instance, **kwargs):
    instance.orden.actualizar_total()