from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
# ==========================================
# 1. CATALOGO Y PRODUCTOS
# ==========================================

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, null=True, blank=True)
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
    
    # COSTO PARA ANÁLISIS FINANCIERO
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Costo promedio o actual del producto para análisis de rentabilidad")
    
    # OPTIMIZACIÓN DE RENDIMIENTO
    # Este campo se actualiza solo (via señales) para no calcular sumas cada vez
    stock_fisico = models.IntegerField(default=0, db_index=True) 
    stock_minimo_global = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.nombre} ({self.stock_fisico})"

    def precio_con_iva(self, iva=0.19):
        """Devuelve el precio incluyendo IVA. Usa Decimal para evitar mezclar tipos."""
        try:
            iva_dec = Decimal(str(iva))
        except Exception:
            iva_dec = Decimal('0.19')
        precio = self.precio_venta if self.precio_venta is not None else Decimal('0')
        result = (precio * (Decimal(1) + iva_dec)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return result
    
    def stock_total(self):
        """Suma el stock_actual de todos los lotes asociados."""
        return sum(lote.stock_actual or 0 for lote in self.lotes.all())

    def obtener_precio_final(self, con_iva=False, iva_pct=0.19):
        """Precio final opcionalmente incluyendo IVA (por defecto 19%)."""
        precio = float(self.precio_venta or 0)
        if con_iva:
            return round(precio * (1 + float(iva_pct)), 2)
        return round(precio, 2)

    def aplicar_descuento(self, porcentaje, aplicar=False):
        """Calcula precio con descuento; si aplicar=True, actualiza el precio y guarda."""
        if porcentaje is None:
            raise ValueError("Porcentaje requerido")
        if porcentaje < 0 or porcentaje > 100:
            raise ValueError("Porcentaje debe estar entre 0 y 100")
        descuento = float(porcentaje) / 100.0
        nuevo_precio = round(float(self.precio_venta) * (1 - descuento), 2)
        if aplicar:
            self.precio_venta = nuevo_precio
            self.save(update_fields=["precio_venta"])
        return nuevo_precio

    def verificar_disponibilidad_general(self, cantidad):
        """Retorna True si la suma de stock en lotes es suficiente."""
        if cantidad is None or cantidad <= 0:
            return False
        return self.stock_total() >= int(cantidad)

class Nutricional(models.Model):
    calorias = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proteinas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    grasas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbohidratos = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    azucares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sodio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name="nutricional")

# ==========================================
# 2. INVENTARIO (LOTES Y COSTOS)
# ==========================================

class Lote(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="lotes")
    numero_lote = models.CharField(max_length=50, null=True, blank=True)
    fecha_elaboracion = models.DateField(null=True, blank=True)
    fecha_caducidad = models.DateField()
    
    # CRÍTICO PARA REPORTES FINANCIEROS
    precio_costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo de compra neto")
    
    stock_inicial = models.IntegerField()
    stock_actual = models.IntegerField(default=0)
    
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

# ==========================================
# 3. ACTORES (CLIENTES Y EMPLEADOS)
# ==========================================

class Cliente(models.Model):
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True) # Null para ventas anonimas
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
    nombres = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=45)
    run = models.CharField(max_length=45, unique=True)
    correo = models.EmailField(max_length=100)
    fono = models.IntegerField(unique=True)
    clave = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    cargo = models.CharField(max_length=45)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.nombres} {self.apellido_paterno}"



# ==========================================
# 4. E-COMMERCE (CARRITO)
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

# ==========================================
# 5. VENTAS Y FACTURACIÓN
# ==========================================

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
    
    # Totales (Se guardan fijos para historial, por si cambia el precio del producto después)
    neto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Estado y Documento
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    tipo_documento = models.CharField(max_length=20, choices=DOC_CHOICES, default='boleta')
    folio_documento = models.CharField(max_length=50, null=True, blank=True, help_text="Folio SII")

    def __str__(self):
        return f"Venta #{self.id} - {self.total}"
    
    def calcular_subtotal(self):
        """Suma cantidad * precio_unitario (sin considerar descuentos) de los detalles."""
        return sum((d.cantidad * float(d.precio_unitario)) for d in self.detalles.all())

    def calcular_total_descuento(self):
        """Suma todos los descuentos aplicados en los detalles."""
        return sum(float(d.descuento) for d in self.detalles.all())

    def calcular_totales_desde_detalles(self):
        """Calcula y actualiza los totales de la venta basados en sus detalles."""
        subtotal = self.calcular_subtotal()
        descuento = self.calcular_total_descuento()
        neto = round(subtotal - descuento, 2)
        iva = round(neto * 0.19, 2)
        total = round(neto + iva, 2)
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

    def actualizar_stock(self):
        """Actualiza el stock de los productos restando las cantidades vendidas, consumiendo lotes por fecha de caducidad ascendente."""
        for detalle in self.detalles.all():
            producto = detalle.producto
            cantidad = detalle.cantidad
            # Consumir lotes por fecha de caducidad (próxima a vencer primero)
            lotes = producto.lotes.filter(stock_actual__gt=0).order_by('fecha_caducidad')
            restante = int(cantidad)
            for lote in lotes:
                if restante <= 0:
                    break
                disponible = lote.stock_actual or 0
                to_retirar = min(disponible, restante)
                if to_retirar > 0:
                    lote.retirar_stock(to_retirar)
                    # crear movimiento de salida
                    MovimientoInventario.objects.create(
                        tipo='salida',
                        cantidad=to_retirar,
                        lote=lote,
                        producto=producto,
                        referencia=f"Venta #{self.id}"
                    )
                    restante -= to_retirar
            if restante > 0:
                raise ValueError(f"Stock insuficiente para producto {producto.nombre}: falta {restante}")

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) # Precio al momento de la venta
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def subtotal(self):
        return (self.cantidad * self.precio_unitario) - self.descuento

class Pago(models.Model):
    METODO_CHOICES = [('EFE', 'Efectivo'), ('DEB', 'Débito'), ('CRE', 'Crédito'), ('TRA', 'Transferencia')]
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=3, choices=METODO_CHOICES)
    referencia_externa = models.CharField(max_length=100, null=True, blank=True, help_text="ID Transbank/Stripe")
    fecha = models.DateTimeField(auto_now_add=True)

#    def __str__(self):
#        return f"Pago {self.monto} ({self.get_metodo_display()})"
#    
# ==========================================
# 6. TRAZABILIDAD (KARDEX)
# ==========================================

# Registro de pagos asociados a una venta
# COMENTADO: Definición duplicada de Pago (la primera definición ya tiene METODO_CHOICES)
# class Pago(models.Model):
#     venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos')
#     monto = models.DecimalField(max_digits=10, decimal_places=2)
#     metodo = models.CharField(max_length=50, null=True, blank=True)
#     fecha = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return f"Pago {self.id} - {self.monto}"


# Movimiento de inventario
class MovimientoInventario(models.Model):
    """
    Registra CADA entrada o salida relacionando Lotes.
    Es la "verdad" contable del inventario.
    """
    TIPO_CHOICES = [('entrada', 'Entrada (Compra)'), ('salida', 'Salida (Venta)'), ('merma', 'Merma/Ajuste')]
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE) # De qué lote salió o entró
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
    
    # Turno de trabajo

class Turno(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='turnos')
    fecha = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField()
    monto_inicial_caja = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_final_caja = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):

        return f"Turno de {self.empleado} el {self.fecha}"
    
# ==========================================
# 7. LOGICA AUTOMÁTICA (SIGNALS)
# ==========================================

@receiver(post_save, sender=Lote)
@receiver(post_save, sender=MovimientoInventario)
def actualizar_stock_producto(sender, instance, **kwargs):
    """
    Cada vez que se toca un lote o un movimiento, 
    se recalcula el stock total del producto y se guarda en caché.
    """
    producto = instance.producto
    total = Lote.objects.filter(producto=producto, eliminado__isnull=True).aggregate(
        total=Sum('stock_actual')
    )['total'] or 0
    
    # Solo guardar si hubo cambio para evitar recursión infinita innecesaria
    if producto.stock_fisico != total:
        producto.stock_fisico = total
        producto.save(update_fields=['stock_fisico'])

# ==========================================
# 8. GASTOS OPERATIVOS
# ==========================================

class GastoOperativo(models.Model):
    TIPO_GASTO_CHOICES = [
        ('alquiler', 'Alquiler'),
        ('servicios', 'Servicios (luz, agua, gas)'),
        ('salarios', 'Salarios'),
        ('marketing', 'Marketing y Publicidad'),
        ('mantenimiento', 'Mantenimiento'),
        ('suministros', 'Suministros'),
        ('transporte', 'Transporte'),
        ('impuestos', 'Impuestos y Licencias'),
        ('otro', 'Otro'),
    ]

    tipo_gasto = models.CharField(max_length=20, choices=TIPO_GASTO_CHOICES)
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    creado = models.DateTimeField(auto_now_add=True)
    es_recurrente = models.BooleanField(default=False, help_text="Si es un gasto mensual fijo")

    class Meta:
        verbose_name = "Gasto Operativo"
        verbose_name_plural = "Gastos Operativos"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_tipo_gasto_display()} - ${self.monto} ({self.fecha})"