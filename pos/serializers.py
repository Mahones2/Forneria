from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from decimal import Decimal
from django.contrib.auth.models import User 
from .models import (
    Categoria, Producto, Nutricional, Lote, MovimientoInventario, 
    Alerta, Cliente, Direccion, Empleado, Turno, Carrito, ItemCarrito, Venta, 
    DetalleVenta, Pago
)
from inventario.models import Proveedor, Insumo, OrdenCompra, OrdenCompraItem, Ubicacion
from dj_rest_auth.serializers import JWTSerializer
# ==========================================
# 1. INPUT SERIALIZERS 
# ==========================================

class ItemVentaInputSerializer(serializers.Serializer):
    """Para validar la lista de productos y cantidades al crear una venta."""
    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)

class PagoInputSerializer(serializers.Serializer):
    """Para validar la información de pago al crear una venta."""
    metodo = serializers.CharField(max_length=3)
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)
    referencia = serializers.CharField(max_length=100, required=False, allow_null=True)
    
   
    monto_recibido = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
     
class VentaInputSerializer(serializers.Serializer):
    """
    Serializer principal para recibir todos los datos de entrada al procesar una Venta.
    """
    items = ItemVentaInputSerializer(many=True)
    pagos = PagoInputSerializer(many=True)
    cliente_id = serializers.IntegerField(required=False, allow_null=True)
    direccion_id = serializers.IntegerField(required=False, allow_null=True)
    canal = serializers.CharField(max_length=10, required=False)


# ==========================================
# 2. ACTORES Y BASICOS 
# ==========================================

class UbicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ubicacion
        fields = '__all__'

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'

class DireccionSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    
    class Meta:
        model = Direccion
        fields = '__all__'

class ClienteSerializer(serializers.ModelSerializer):
    direcciones = DireccionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cliente
        fields = '__all__'

# users/serializers.py
class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Crea el User y hashea la contraseña
        user = User.objects.create_user(**validated_data)
        return user

class EmpleadoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source='__str__', read_only=True)
    
    class Meta:
        model = Empleado
        fields = '__all__'

# empleados/serializers.py
class EmpleadoCreateSerializer(serializers.ModelSerializer):
    usuario = UserCreateSerializer() 

    class Meta:
        model = Empleado
        # Necesitas todos los campos del Empleado, menos la relación 'usuario' 
        # (que ahora es el serializador anidado)
        fields = ['run', 'fono', 'direccion', 'cargo', 'usuario'] 

    def create(self, validated_data):
        # 1. Extrae los datos del User anidado
        user_data = validated_data.pop('usuario')

        # 2. Crea el objeto User
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data.get('email', ''), # Usar get() si el campo es opcional
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            password=user_data['password']
        )

        # 3. Crea el objeto Empleado, vinculándolo al User
        empleado = Empleado.objects.create(usuario=user, **validated_data)
        return empleado

class CustomJWTSerializer(JWTSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        try:
            empleado = Empleado.objects.get(usuario=user)
            cargo = empleado.cargo
        except Empleado.DoesNotExist:
            cargo = None

        data['user']['cargo'] = cargo
        data['user']['groups'] = list(user.groups.values_list("name", flat=True))
        return data

class TurnoSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.__str__', read_only=True)

    class Meta:
        model = Turno
        fields = '__all__'

# ==========================================
# 3. PRODUCTOS Y CATALOGO
# ==========================================

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class NutricionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nutricional
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    nutricional = NutricionalSerializer(read_only=True)
    precio_con_iva = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = '__all__'
        read_only_fields = ['stock_fisico']

    def get_precio_con_iva(self, obj):
        return obj.precio_con_iva()

# ==========================================
# 4. INVENTARIO Y ABASTECIMIENTO
# ==========================================

class InsumoSerializer(serializers.ModelSerializer):
    # Se añade allow_null=True para evitar errores si no hay proveedor/ubicación
    proveedor_nombre = serializers.CharField(source='proveedor_preferido.nombre', read_only=True, allow_null=True)
    ubicacion_nombre = serializers.CharField(source='ubicacion.nombre', read_only=True, allow_null=True)

    class Meta:
        model = Insumo
        fields = '__all__'

class OrdenCompraItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrdenCompraItem
        fields = '__all__'
    
    def get_subtotal(self, obj):
        return obj.subtotal()

class OrdenCompraSerializer(serializers.ModelSerializer):
    items = OrdenCompraItemSerializer(many=True, read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)

    class Meta:
        model = OrdenCompra
        fields = '__all__'
        read_only_fields = ['total']

class LoteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lote
        fields = '__all__'
        read_only_fields = ['stock_actual']

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    
    class Meta:
        model = MovimientoInventario
        fields = '__all__'

class AlertaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True, allow_null=True)
    
    class Meta:
        model = Alerta
        fields = '__all__'

# ==========================================
# 5. VENTAS Y E-COMMERCE
# ==========================================

class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    precio_unitario = serializers.DecimalField(source='producto.precio_venta', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = ItemCarrito
        fields = '__all__'

    def get_subtotal(self, obj):
        return obj.subtotal()

class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)
    total_neto = serializers.SerializerMethodField() 
    total_bruto = serializers.SerializerMethodField() 

    class Meta:
        model = Carrito
        fields = '__all__'
        
    def get_total_bruto(self, obj):
        return sum(item.subtotal() for item in obj.items.all())

    def get_total_neto(self, obj):
        total_bruto = self.get_total_bruto(obj)
        # Asumiendo un 19% de IVA (factor 1.19)
        return total_bruto / Decimal('1.19')


class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    # Utilizamos el método subtotal del modelo como un campo SerializerMethodField
    subtotal = serializers.SerializerMethodField() 

    class Meta:
        model = DetalleVenta
        # Aseguramos que se envíen todos los campos que el frontend necesita
        fields = ['producto_nombre', 'cantidad', 'precio_unitario', 'descuento', 'subtotal'] 
    
    def get_subtotal(self, obj):
        # Llama al método subtotal() del modelo DetalleVenta
        return obj.subtotal()

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'

class VentaSerializer(serializers.ModelSerializer):
    # --- CAMPOS DE ESCRITURA (Write-Only) ---
    
    # 1. Recibe el ID del cliente desde el frontend (POS)
    cliente_id = serializers.IntegerField(write_only=True, required=False, allow_null=True) 
    
    # 2. Recibe los ítems del carrito (que luego se convierten en DetalleVenta)
    items = serializers.ListField(write_only=True, child=serializers.DictField(), required=False) 
    
    # --- CAMPOS DE LECTURA (Read-Only) ---

    # 3. Detalle y Pagos anidados (solo lectura)
    detalles = DetalleVentaSerializer(many=True, required=False, read_only=True)
    pagos = PagoSerializer(many=True, required=False, read_only=True)
    
    # 4. Obtener Nombre/RUT del Cliente (Solución al "Consumidor Final")
    cliente_nombre = serializers.SerializerMethodField()
    cliente_rut = serializers.SerializerMethodField()
    
    # 5. Nombre del Vendedor (asumiendo relación Empleado -> Usuario)
    vendedor_nombre = serializers.CharField(source='empleado__usuario__first_name', read_only=True, allow_null=True)

    class Meta:
        model = Venta
        fields = (
            'id', 'cliente', 'cliente_id', 'cliente_nombre', 'cliente_rut', 
            'vendedor_nombre', 'detalles', 'pagos', 'items', 'neto', 'iva', 
            'total', 'fecha', 'folio_documento', 'estado', 'costo_envio'
        )
        # Campos que DRF no debe intentar guardar, ya que los calculamos o son de solo lectura.
        read_only_fields = ['neto', 'iva', 'total', 'fecha', 'folio_documento', 'cliente', 'detalles', 'estado']
        
    # --- MÉTODOS DE LECTURA (SerializerMethodField) ---
    
    def get_cliente_nombre(self, obj):
        """Devuelve el nombre del cliente o 'Consumidor Final' si es nulo."""
        if obj.cliente:
            return obj.cliente.nombre
        return 'Consumidor Final'

    def get_cliente_rut(self, obj):
        """Devuelve el RUT del cliente o None si es nulo."""
        if obj.cliente:
            return obj.cliente.rut
        return None
    
    # --- MÉTODO DE ESCRITURA (CREATE) ---

    def create(self, validated_data):
        # --- 1. Extraer listas anidadas y claves de control ---
        items_data = validated_data.pop('items', [])
        pagos_data = validated_data.pop('pagos', [])
        cliente_id = validated_data.pop('cliente_id', None)
        
        # Eliminar el campo redundante 'detalles' si existe para evitar conflictos
        validated_data.pop('detalles', None) 

        # --- 2. MANEJO DEL CLIENTE ---
        if cliente_id:
            try:
                # Busca el objeto Cliente y lo asigna al campo 'cliente'
                validated_data['cliente'] = Cliente.objects.get(id=cliente_id)
            except Cliente.DoesNotExist:
                validated_data['cliente'] = None
        else:
             validated_data['cliente'] = None 

        # --- 3. Asignar empleado y calcular Total ---
        request = self.context.get('request', None)
        # Asume que el usuario autenticado tiene una relación 'empleado'
        empleado = request.user.empleado if request and hasattr(request.user, 'empleado') else None
        
        # Recalcular el total y asignar empleado
        total_calculado = sum(
            Decimal(item['precio_unitario']) * item['cantidad'] for item in items_data
        )

        validated_data['empleado'] = empleado
        validated_data['total'] = total_calculado
        
        # --- 4. Crear el objeto Venta ---
        venta = Venta.objects.create(**validated_data)

        # --- 5. Crear DetalleVenta (Items) ---
        for item_data in items_data:
            # Asegúrate de que 'producto_id' existe en item_data
            try:
                producto = Producto.objects.get(id=item_data['producto_id'])
            except Producto.DoesNotExist:
                # Manejo de error si el producto no existe (debes decidir si abortar la venta o registrar un error)
                raise serializers.ValidationError(f"Producto con ID {item_data.get('producto_id')} no encontrado.")

            DetalleVenta.objects.create(
                venta=venta, 
                producto=producto, 
                cantidad=item_data['cantidad'],
                precio_unitario=item_data['precio_unitario'] 
            )

        # --- 6. Crear Pagos ---
        for pago_data in pagos_data:
            Pago.objects.create(venta=venta, **pago_data)
            
        return venta