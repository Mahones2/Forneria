from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from decimal import Decimal
from django.contrib.auth.models import User 
from dj_rest_auth.serializers import JWTSerializer
from django.db import transaction

# Modelos
from .models import (
    Categoria, Producto, Nutricional, Lote, MovimientoInventario, 
    Alerta, Cliente, Direccion, Empleado, Turno, Proveedor, Insumo, 
    OrdenCompra, OrdenCompraItem, Carrito, ItemCarrito, Venta, 
    DetalleVenta, Pago, Ubicacion
)

# ==========================================
# 1. INPUT SERIALIZERS (VALIDACIÓN DE ENTRADA)
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
    fecha_entrega = serializers.DateField(required=False, allow_null=True)


# ==========================================
# 2. ACTORES Y BÁSICOS (USUARIOS, CLIENTES, ETC)
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
    # Campo de solo lectura calculado en la vista (annotate)
    total_compras = serializers.IntegerField(read_only=True) 
    direcciones = DireccionSerializer(many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = '__all__'

# --- GESTIÓN DE USUARIOS Y EMPLEADOS (FUSIÓN MEJORADA) ---

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializador auxiliar para crear el usuario de Django dentro del Empleado."""
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class EmpleadoCreateSerializer(serializers.ModelSerializer):
    """
    USADO PARA CREAR: Usa la estructura anidada de tu compañera.
    Es más limpio y seguro.
    """
    usuario = UserCreateSerializer() 

    class Meta:
        model = Empleado
        fields = ['run', 'fono', 'direccion', 'cargo', 'usuario'] 

    def create(self, validated_data):
        # Transacción atómica para asegurar que se crean ambos o ninguno
        with transaction.atomic():
            user_data = validated_data.pop('usuario')
            
            # Reutilizamos la lógica del UserCreateSerializer
            user_serializer = UserCreateSerializer(data=user_data)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()

            empleado = Empleado.objects.create(usuario=user, **validated_data)
            return empleado

class EmpleadoSerializer(serializers.ModelSerializer):
    """
    USADO PARA LISTAR/EDITAR: Usa TU lógica avanzada de actualización.
    """
    nombre_completo = serializers.SerializerMethodField()
    username = serializers.CharField(source='usuario.username') # Editable
    cargo = serializers.ChoiceField(choices=Empleado.CARGO_CHOICES, required=True)

    class Meta:
        model = Empleado
        fields = ['id', 'nombre_completo', 'username', 'cargo', 'run', 'fono', 'direccion']

    def get_nombre_completo(self, obj):
        first = obj.usuario.first_name or ''
        last = obj.usuario.last_name or ''
        full = (first + ' ' + last).strip()
        return full if full else obj.usuario.username

    def validate_username(self, value):
        # Validación de unicidad personalizada de TU código
        if ' ' in value:
            raise serializers.ValidationError("El username no debe contener espacios")
        qs = User.objects.filter(username=value)
        instance = getattr(self, 'instance', None)
        if instance:
            qs = qs.exclude(pk=instance.usuario_id)
        if qs.exists():
            raise serializers.ValidationError("El username ya está en uso")
        return value

    def update(self, instance, validated_data):
        # TU lógica de actualización (Code A) es superior aquí
        usuario_data = validated_data.get('usuario', {})
        new_username = usuario_data.get('username')
        
        # Actualizar Username en modelo User
        if new_username and new_username != instance.usuario.username:
            instance.usuario.username = new_username
            instance.usuario.save(update_fields=['username'])
            
        # Actualizar campos propios de Empleado
        if 'cargo' in validated_data:
            instance.cargo = validated_data['cargo']
        if 'run' in validated_data:
            instance.run = validated_data['run']
        if 'fono' in validated_data:
            instance.fono = validated_data['fono']
        if 'direccion' in validated_data:
            instance.direccion = validated_data['direccion']
            
        instance.save()
        return instance

class CustomJWTSerializer(JWTSerializer):
    """Agrega cargo y grupos al token JWT."""
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
    empleado_nombre = serializers.CharField(source='empleado.usuario.get_full_name', read_only=True)

    class Meta:
        model = Turno
        fields = '__all__'


# ==========================================
# 3. PRODUCTOS Y CATÁLOGO
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
        return total_bruto / Decimal('1.19')


class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    subtotal = serializers.SerializerMethodField() 

    class Meta:
        model = DetalleVenta
        fields = ['producto_nombre', 'cantidad', 'precio_unitario', 'descuento', 'subtotal'] 
    
    def get_subtotal(self, obj):
        return obj.subtotal()

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'

class VentaSerializer(serializers.ModelSerializer):
    # --- CAMPOS DE ESCRITURA (Write-Only) ---
    cliente_id = serializers.IntegerField(write_only=True, required=False, allow_null=True) 
    items = serializers.ListField(write_only=True, child=serializers.DictField(), required=False) 
    
    # --- CAMPOS DE LECTURA (Read-Only) ---
    detalles = DetalleVentaSerializer(many=True, required=False, read_only=True)
    pagos = PagoSerializer(many=True, required=False, read_only=True)
    
    cliente_nombre = serializers.SerializerMethodField()
    cliente_rut = serializers.SerializerMethodField()
    vendedor_nombre = serializers.CharField(source='empleado.usuario.first_name', read_only=True, allow_null=True)

    class Meta:
        model = Venta
        fields = (
            'id', 'cliente', 'cliente_id', 'cliente_nombre', 'cliente_rut', 
            'vendedor_nombre', 'detalles', 'pagos', 'items', 'neto', 'iva', 
            'total', 'fecha', 'folio_documento', 'estado', 'costo_envio', 'fecha_entrega'
        )
        read_only_fields = ['neto', 'iva', 'total', 'fecha', 'folio_documento', 'cliente', 'detalles', 'estado', 'fecha_entrega']
        
    def get_cliente_nombre(self, obj):
        if obj.cliente:
            return obj.cliente.nombre
        return 'Consumidor Final'

    def get_cliente_rut(self, obj):
        if obj.cliente:
            return obj.cliente.rut
        return None
    
    def create(self, validated_data):
        # Esta lógica es útil si se usa el Serializer directamente para crear,
        # aunque tu ViewSet usa principalmente 'procesar_venta' del servicio.
        items_data = validated_data.pop('items', [])
        pagos_data = validated_data.pop('pagos', [])
        cliente_id = validated_data.pop('cliente_id', None)
        validated_data.pop('detalles', None) 

        if cliente_id:
            try:
                validated_data['cliente'] = Cliente.objects.get(id=cliente_id)
            except Cliente.DoesNotExist:
                validated_data['cliente'] = None
        else:
             validated_data['cliente'] = None 

        request = self.context.get('request', None)
        empleado = request.user.empleado if request and hasattr(request.user, 'empleado') else None
        
        total_calculado = sum(
            Decimal(item['precio_unitario']) * item['cantidad'] for item in items_data
        )

        validated_data['empleado'] = empleado
        validated_data['total'] = total_calculado
        
        venta = Venta.objects.create(**validated_data)

        for item_data in items_data:
            producto = Producto.objects.get(id=item_data['producto_id'])
            DetalleVenta.objects.create(
                venta=venta, 
                producto=producto, 
                cantidad=item_data['cantidad'],
                precio_unitario=item_data['precio_unitario'] 
            )

        for pago_data in pagos_data:
            Pago.objects.create(venta=venta, **pago_data)
            
        return venta