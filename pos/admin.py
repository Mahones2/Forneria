from django.contrib import admin
from django.db.models import Sum
from .models import *

# ==========================================
# INLINES (Para editar modelos relacionados dentro del padre)
# ==========================================

# 1. Lotes dentro de Producto
class LoteInline(admin.TabularInline):
    model = Lote
    extra = 1 # Mostrar un formulario vacío para añadir un nuevo lote
    # Campos que el admin puede editar directamente en la tabla
    fields = [
        'numero_lote', 'precio_costo_unitario', 'fecha_caducidad', 
        'stock_inicial', 'stock_actual', 'eliminado'
    ]
    readonly_fields = ['stock_actual'] # El stock se modifica por movimientos


# 2. Detalles de Venta dentro de Venta
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ['producto', 'cantidad', 'precio_unitario', 'descuento', 'subtotal']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False # Los detalles se crean con el servicio procesar_venta, no manualmente

# 3. Pagos dentro de Venta
class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    readonly_fields = ['monto', 'metodo', 'referencia_externa', 'fecha']
    can_delete = False
    
# 4. Direcciones dentro de Cliente
class DireccionInline(admin.TabularInline):
    model = Direccion
    extra = 1


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # CRÍTICO: Muestra el stock cacheado y el precio con IVA
    list_display = (
        'codigo_barra', 'nombre', 'marca', 'precio_venta', 'precio_con_iva', 
        'stock_fisico', 'categoria', 'stock_minimo_global'
    )
    # Permite buscar eficientemente por nombre, código y marca
    search_fields = ('nombre', 'codigo_barra', 'marca')
    # Permite filtrar por marca y categoría
    list_filter = ('marca', 'categoria')
    # Campos que se pueden editar directamente en la lista
    list_editable = ('precio_venta', 'stock_minimo_global')
    # Organiza los campos en el formulario de edición
    fieldsets = (
        (None, {'fields': ('nombre', 'descripcion', 'codigo_barra', 'categoria')}),
        ('Información Comercial', {'fields': ('marca', 'precio_venta', 'tipo', 'presentacion')}),
        ('Inventario', {'fields': ('stock_fisico', 'stock_minimo_global',)}),
    )
    readonly_fields = ('stock_fisico',) # stock_fisico es solo lectura, se actualiza por señales
    inlines = [LoteInline]
    
    # Define la columna calculada (precio_con_iva es un método del modelo)
    def precio_con_iva(self, obj):
        return f"${obj.precio_con_iva()}"
    precio_con_iva.short_description = 'Precio Final (IVA 19%)'


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    # CRÍTICO: Muestra el costo unitario, stock y si está vencido
    list_display = (
        'producto', 'numero_lote', 'fecha_caducidad', 'precio_costo_unitario', 
        'stock_actual', 'stock_inicial', 'esta_vencido'
    )
    list_filter = ('producto', 'fecha_caducidad')
    search_fields = ('producto__nombre', 'numero_lote')
    list_editable = ['precio_costo_unitario'] 
    readonly_fields = ['stock_actual']
    
    # Columna para el estado de vencimiento
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
    # Campos solo de lectura (los totales los calcula el servicio)
    readonly_fields = ('neto', 'iva', 'total', 'fecha', 'empleado')
    
    # Permite ver el detalle y el pago dentro de la venta
    inlines = [DetalleVentaInline, PagoInline]
    
    # Bloquea la creación manual en el admin; la creación debe pasar por el servicio procesar_venta
    def has_add_permission(self, request):
        return False 
    
    # Permite actualizar el estado 
    fieldsets = (
        ('Detalle de la Venta', {'fields': ('id', 'fecha', 'empleado', 'cliente', 'direccion_despacho')}),
        ('Totales y Documentación', {'fields': ('neto', 'iva', 'total', 'costo_envio', 'tipo_documento', 'folio_documento')}),
        ('Logística y Estado', {'fields': ('canal_venta', 'estado')}),
    )

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
    readonly_fields = ('fecha', 'usuario') # No se recomienda manipular movimientos, solo auditarlos
    
    # Bloquea la edición para mantener la trazabilidad
    def has_change_permission(self, request, obj=None):
        return False
    
    # Bloquea la eliminación para mantener la auditoría
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'run', 'cargo', 'fono')
    search_fields = ('usuario__first_name', 'usuario__last_name', 'run')
    list_filter = ('cargo',)

# Registro simple de modelos sin configuración especial
admin.site.register(Categoria)
admin.site.register(Nutricional)
admin.site.register(Alerta)
admin.site.register(Turno)
