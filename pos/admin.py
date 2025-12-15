from django.contrib import admin
from django.db.models import Sum
from .models import *

# ==========================================
# INLINES (Para editar modelos relacionados dentro del padre)
# ==========================================

# 1. Lotes dentro de Producto
class LoteInline(admin.TabularInline):
    model = Lote
    extra = 1 
    fields = [
        'numero_lote', 'precio_costo_unitario', 'fecha_caducidad', 
        'stock_inicial', 'stock_actual', 'eliminado'
    ]
    readonly_fields = ['stock_actual'] 

# 2. Detalles de Venta dentro de Venta
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    # Agregamos subtotal como columna calculada
    readonly_fields = ['producto', 'cantidad', 'precio_unitario', 'descuento', 'subtotal_calculado']
    can_delete = False
    
    def subtotal_calculado(self, obj):
        return obj.subtotal()
    subtotal_calculado.short_description = 'Subtotal'
    
    def has_add_permission(self, request, obj=None):
        return False

# 3. Pagos dentro de Venta
class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    # CRÍTICO: Añadir vuelto y monto_recibido al readonly_fields
    readonly_fields = ['monto', 'metodo', 'referencia_externa', 'monto_recibido', 'vuelto', 'fecha']
    can_delete = False
    
# 4. Direcciones dentro de Cliente
class DireccionInline(admin.TabularInline):
    model = Direccion
    extra = 1

# 5. Items de Orden de Compra dentro de OrdenCompra
class OrdenCompraItemInline(admin.TabularInline):
    model = OrdenCompraItem
    extra = 1
    fields = ['insumo', 'cantidad', 'precio_unitario', 'subtotal_calculado']
    readonly_fields = ['subtotal_calculado']
    
    def subtotal_calculado(self, obj):
        return obj.subtotal()
    subtotal_calculado.short_description = 'Subtotal'


# ==========================================
# REGISTRO DE MODELOS PRINCIPALES
# ==========================================

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # ... (El código de ProductoAdmin se mantiene igual)
    list_display = (
        'codigo_barra', 'nombre', 'marca', 'precio_venta', 'precio_con_iva', 
        'stock_fisico', 'categoria', 'stock_minimo_global'
    )
    search_fields = ('nombre', 'codigo_barra', 'marca')
    list_filter = ('marca', 'categoria')
    list_editable = ('precio_venta', 'stock_minimo_global')
    fieldsets = (
        (None, {'fields': ('nombre', 'descripcion', 'codigo_barra', 'categoria', 'imagen_url')}),
        ('Información Comercial', {'fields': ('marca', 'precio_venta', 'tipo', 'presentacion')}),
        ('Inventario', {'fields': ('stock_fisico', 'stock_minimo_global',)}),
    )
    readonly_fields = ('stock_fisico', 'imagen_url') 
    inlines = [LoteInline]
    
    def precio_con_iva(self, obj):
        return f"${obj.precio_con_iva()}"
    precio_con_iva.short_description = 'Precio Final (IVA 19%)'
# ... (Continúa el resto de los administradores existentes) ...


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = (
        'producto', 'numero_lote', 'fecha_caducidad', 'precio_costo_unitario', 
        'stock_actual', 'stock_inicial', 'esta_vencido'
    )
    list_filter = ('producto', 'fecha_caducidad', 'ubicacion')
    search_fields = ('producto__nombre', 'numero_lote')
    list_editable = ['precio_costo_unitario'] 
    readonly_fields = ['stock_actual']
    
    def esta_vencido(self, obj):
        return obj.esta_vencido
    esta_vencido.boolean = True
    esta_vencido.short_description = 'Vencido'

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'fecha', 'cliente', 'empleado', 'total', 'estado', 
        'canal_venta', 'tipo_documento', 'folio_documento'
    )
    list_filter = ('estado', 'canal_venta', 'tipo_documento', 'fecha')
    search_fields = ('cliente__nombre', 'cliente__rut', 'folio_documento')
    
    # MODIFICACIÓN CLAVE AQUÍ: Añadir 'id_display' y 'fecha' al readonly
    readonly_fields = ('id_display', 'neto', 'iva', 'total', 'fecha', 'empleado')
    
    inlines = [DetalleVentaInline, PagoInline]
    
    def has_add_permission(self, request):
        return False 
    
    # CORRECCIÓN EN FIELDSETS: Usar 'id_display' en lugar de 'id'
    fieldsets = (
        ('Detalle de la Venta', {'fields': ('id_display', 'fecha', 'empleado', 'cliente', 'direccion_despacho')}),
        ('Totales y Documentación', {'fields': ('neto', 'iva', 'total', 'costo_envio', 'tipo_documento', 'folio_documento')}),
        ('Logística y Estado', {'fields': ('canal_venta', 'estado')}),
    )

    # NUEVO MÉTODO PARA MOSTRAR EL ID
    def id_display(self, obj):
        # Retorna el ID de la instancia de Venta (obj)
        return obj.id
    id_display.short_description = 'ID de Venta'
    id_display.admin_order_field = 'id' # Permite ordenar por la columna ID

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'correo', 'telefono', 'es_empresa')
    search_fields = ('nombre', 'rut', 'correo')
    list_filter = ('es_empresa',)
    inlines = [DireccionInline]


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'producto', 'lote', 'cantidad', 'tipo', 'referencia')
    list_filter = ('tipo', 'producto', 'fecha')
    search_fields = ('producto__nombre', 'referencia', 'lote__numero_lote')
    readonly_fields = ('fecha', 'usuario')
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'run', 'cargo', 'fono')
    search_fields = ('usuario__first_name', 'usuario__last_name', 'run')
    list_filter = ('cargo',)

# ==========================================
# REGISTROS FALTANTES
# ==========================================

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'unidad_medida', 'stock_actual', 'stock_minimo', 'proveedor_preferido')
    search_fields = ('nombre', 'unidad_medida')
    list_filter = ('proveedor_preferido', 'ubicacion')
    list_editable = ('stock_minimo',)
    readonly_fields = ('stock_actual',)
    fieldsets = (
        (None, {'fields': ('nombre', 'descripcion', 'unidad_medida', 'proveedor_preferido', 'ubicacion')}),
        ('Inventario', {'fields': ('stock_actual', 'stock_minimo')}),
    )

@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'proveedor', 'fecha', 'estado', 'total')
    list_filter = ('estado', 'proveedor', 'fecha')
    readonly_fields = ('total', 'fecha')
    inlines = [OrdenCompraItemInline]
    # Se añade un botón para actualizar el total manualmente si fuera necesario
    actions = ['recalcular_total']
    
    def recalcular_total(self, request, queryset):
        for orden in queryset:
            orden.actualizar_total()
        self.message_user(request, f"Total(es) de {queryset.count()} Orden(es) de Compra recalculado(s) con éxito.")
    recalcular_total.short_description = "Recalcular Total de OC"

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'contacto', 'telefono', 'correo')
    search_fields = ('nombre', 'contacto')

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

# --- Modelos ya registrados o usados en Inlines ---
# @admin.register(DetalleVenta) y @admin.register(Pago) no son necesarios si solo se ven en Venta.
# Si quieres ver la tabla de todos los pagos o detalles, usa el registro base:
@admin.register(DetalleVenta)
class DetalleVentaBaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'producto', 'cantidad', 'precio_unitario', 'subtotal')
    readonly_fields = list_display
    search_fields = ('venta__id', 'producto__nombre')
    list_filter = ('venta',)

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Pago)
class PagoBaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'metodo', 'monto', 'monto_recibido', 'vuelto', 'fecha')
    readonly_fields = list_display
    search_fields = ('venta__id', 'referencia_externa')
    list_filter = ('metodo',)
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False


# Registro de modelos de E-commerce
class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0
    readonly_fields = ['producto', 'cantidad', 'subtotal']

@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'session_key', 'creado', 'actualizado')
    inlines = [ItemCarritoInline]
    readonly_fields = ('creado', 'actualizado')
    search_fields = ('cliente__nombre', 'session_key')

admin.site.register(Categoria)
admin.site.register(Nutricional)
admin.site.register(Alerta)
admin.site.register(Turno)