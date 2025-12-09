from django.contrib import admin
from .models import Proveedor, Ubicacion, Insumo, OrdenCompra, OrdenCompraItem


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'contacto', 'correo', 'telefono')


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'descripcion')


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'unidad_medida', 'stock_actual', 'stock_minimo', 'proveedor', 'ubicacion')
	list_filter = ('proveedor', 'ubicacion')


class OrdenCompraItemInline(admin.TabularInline):
	model = OrdenCompraItem
	extra = 0


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
	list_display = ('id', 'proveedor', 'fecha', 'estado', 'total')
	inlines = [OrdenCompraItemInline]
