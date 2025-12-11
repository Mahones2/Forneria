from django.db import models


# Proveedor: datos básicos sobre proveedores de insumos
class Proveedor(models.Model):
	nombre = models.CharField(max_length=150)
	contacto = models.CharField(max_length=150, null=True, blank=True)
	correo = models.EmailField(null=True, blank=True)
	telefono = models.CharField(max_length=50, null=True, blank=True)
	direccion = models.CharField(max_length=250, null=True, blank=True)

	def __str__(self):
		return self.nombre


# Ubicación física en almacén o bodega
class Ubicacion(models.Model):
	nombre = models.CharField(max_length=100)
	descripcion = models.CharField(max_length=250, null=True, blank=True)

	def __str__(self):
		return self.nombre


# Insumos que no son productos terminados (harinas, levaduras, etc.)
class Insumo(models.Model):
	nombre = models.CharField(max_length=150)
	descripcion = models.TextField(null=True, blank=True)
	unidad_medida = models.CharField(max_length=50, null=True, blank=True)
	stock_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='insumos')
	ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='insumos')

	def __str__(self):
		return self.nombre


# Orden de compra y líneas para pedir insumos
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


class OrdenCompraItem(models.Model):
	orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='items')
	insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
	cantidad = models.DecimalField(max_digits=10, decimal_places=2)
	precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

	def subtotal(self):
		return float(self.cantidad) * float(self.precio_unitario)

