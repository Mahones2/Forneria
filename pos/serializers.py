from rest_framework import serializers
from .models import * 
from datetime import date, datetime
from django.db.models import Sum, F
import re

# ==========================================
# 1. CATALOGO Y PRODUCTOS
# ==========================================

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class NutricionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nutricional
        fields = '__all__'
    # (Tus validaciones para calorías, proteinas, etc., se mantienen y son correctas)
    def validate_calorias(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Las calorias no pueden ser negativas.")
        return value
    # ... (Otras validaciones de campos nutricionales...)


class LoteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    
    class Meta:
        model = Lote
        # ¡IMPORTANTE! Agregado precio_costo_unitario (para reportes de ganancia)
        fields = [
            'id', 'numero_lote', 'fecha_elaboracion', 'fecha_caducidad',
            'stock_actual', 'precio_costo_unitario', 'producto', 'producto_nombre'
        ]
        read_only_fields = ['id', 'stock_actual', 'producto_nombre'] # El stock_actual se maneja con movimientos

    def validate(self, data):
        # (Tus validaciones de fechas y stocks se mantienen y son correctas)
        if data.get("fecha_elaboracion") and data.get("fecha_caducidad"):
            if data["fecha_caducidad"] <= data["fecha_elaboracion"]:
                raise serializers.ValidationError({
                    "fecha_caducidad": "La fecha de caducidad debe ser posterior a la fecha de elaboración."
                })
        
        # Validación de caducidad en el pasado
        if data.get("fecha_caducidad") and data["fecha_caducidad"] < date.today():
             raise serializers.ValidationError({
                 "fecha_caducidad": "La fecha de caducidad no puede estar en el pasado."
             })
             
        # El stock_actual no se valida aquí en create/update, se maneja por MovimientoInventario
        return data


class ProductoSerializer(serializers.ModelSerializer):
    nutricional = NutricionalSerializer(read_only=True)
    lotes = LoteSerializer(many=True, read_only=True)
    
    # CRÍTICO: Usamos el campo físico cacheado para rendimiento
    stock_total = serializers.IntegerField(source='stock_fisico', read_only=True) 
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Producto
        # Importante: precio fue renombrado a precio_venta en el nuevo modelo
        fields = [
            'id', 'codigo_barra', 'nombre', 'descripcion', 'marca',
            'precio_venta', 'tipo', 'presentacion', 'categoria', 
            'stock_total', 'nutricional', 'lotes', 'categoria_nombre'
        ]

    def validate_precio_venta(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio de venta debe ser mayor a 0.")
        return value


# ==========================================
# 2. ACTORES Y LOGISTICA
# ==========================================

class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = '__all__'
        read_only_fields = ['cliente'] 

class ClienteSerializer(serializers.ModelSerializer):
    direcciones = DireccionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cliente
        fields = ['id', 'rut', 'nombre', 'correo', 'telefono', 'es_empresa', 'direcciones']
    
    def validate_rut(self, value):
        if not value:
            raise serializers.ValidationError("El RUT es obligatorio.")

        # Validar formato: 7 u 8 dígitos + guion + dígito verificador (número o K)
        patron = r'^\d{7,8}-[\dkK]$'
        if not re.match(patron, value):
            raise serializers.ValidationError("El RUT debe tener el formato 12345678-5")

        return value

class EmpleadoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = Empleado
        fields = [
            'id', 'run', 'fono', 'direccion', 'cargo', 
            'usuario', 'nombre_completo'
        ]
        

class TurnoSerializer(serializers.ModelSerializer):
    # Campo de solo lectura para mostrar el nombre del empleado
    empleado_nombre = serializers.CharField(source='empleado.__str__', read_only=True)
    
    class Meta:
        model = Turno
        fields = [
            'id', 'empleado', 'empleado_nombre', 
            'fecha', 'hora_entrada', 'hora_salida', # <-- Campos reales del modelo
            'monto_inicial_caja', 'monto_final_caja'
        ]
        # 'fecha' y 'hora_entrada' se usan al crear/iniciar. 'hora_salida' se actualiza.
        read_only_fields = ['fecha'] 

    def validate(self, data):
        # La fecha y hora de entrada deben existir si estamos creando o actualizando
        fecha = data.get('fecha', getattr(self.instance, 'fecha', None))
        hora_entrada = data.get('hora_entrada', getattr(self.instance, 'hora_entrada', None))
        hora_salida = data.get('hora_salida')

        # Si estamos creando o actualizando una entrada/salida, necesitamos los datos base
        if not fecha or not hora_entrada:
            # Esto solo debería ocurrir si no es una instancia existente y faltan datos
            return data

        # 1. Combinar la fecha con las horas para crear objetos datetime comparables
        try:
            # Si es una instancia existente (actualización), usa los valores existentes si no se proporcionan nuevos
            fecha_dt = datetime.combine(fecha, hora_entrada) 
        except TypeError:
            # Esto puede ocurrir si 'fecha' no es un date object (ya estaba validado)
             raise serializers.ValidationError({"fecha": "Formato de fecha no válido."})

        # Validación 1: Monto inicial
        monto_inicial = data.get('monto_inicial_caja')
        if monto_inicial is not None and monto_inicial < 0:
            raise serializers.ValidationError({
                "monto_inicial_caja": "El monto inicial de la caja no puede ser negativo."
            })
            
        # Validación 2: Hora de salida no puede ser anterior a la de entrada
        if hora_salida:
            hora_entrada_dt = datetime.combine(fecha, hora_entrada)
            hora_salida_dt = datetime.combine(fecha, hora_salida)

            if hora_salida_dt <= hora_entrada_dt:
                raise serializers.ValidationError({
                    "hora_salida": "La hora de salida debe ser posterior a la hora de entrada."
                })
        
        return data
        
# ==========================================
# 3. VENTA Y TRAZABILIDAD
# ==========================================

class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = DetalleVenta
        fields = ['id', 'cantidad', 'precio_unitario', 'descuento', 'producto', 'producto_nombre']
        read_only_fields = ['id']

    
    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return value

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        # ¡IMPORTANTE! 'referencia' fue renombrado a 'referencia_externa'
        fields = ['id', 'monto', 'metodo', 'referencia_externa', 'fecha']
        read_only_fields = ['id', 'fecha']


class VentaSerializer(serializers.ModelSerializer):
  
    cliente_info = ClienteSerializer(source='cliente', read_only=True)
    empleado_info = EmpleadoSerializer(source='empleado', read_only=True)
    direccion_despacho_info = DireccionSerializer(source='direccion_despacho', read_only=True)
    
    detalles = DetalleVentaSerializer(many=True, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)

    total_pagado = serializers.SerializerMethodField()
    saldo_pendiente = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        
        fields = [
            'id', 'fecha', 'neto', 'iva', 'total', 'costo_envio',
            'canal_venta', 'tipo_documento', 'folio_documento',
            'cliente', 'cliente_info', 'empleado', 'empleado_info', 
            'direccion_despacho_info',
            'detalles', 'pagos', 'total_pagado', 'saldo_pendiente'
        ]
        read_only_fields = fields 

    def get_total_pagado(self, obj):
        # Utiliza la agregación de Django
        return obj.pagos.aggregate(total=Sum('monto'))['total'] or 0

    def get_saldo_pendiente(self, obj):
        return obj.total - self.get_total_pagado(obj)


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    lote_info = LoteSerializer(source='lote', read_only=True)
    
    class Meta:
        model = MovimientoInventario
        fields = [
            'id', 'tipo', 'cantidad', 'fecha', 'producto', 
            'lote', 'lote_info', 'referencia', 'usuario'
        ]
        
    def validate(self, data):
        # Validar que la fecha no sea futura
        if data.get("fecha") and data["fecha"] > datetime.now():
            raise serializers.ValidationError({"fecha": "La fecha del movimiento no puede estar en el futuro."})

        return data
    
    
class VentaInputSerializer(serializers.Serializer):
    """Serializer usado SÓLO para recibir datos de entrada al servicio procesar_venta."""
    cliente_rut = serializers.CharField(max_length=12, required=False, allow_blank=True)
    canal_venta = serializers.ChoiceField(choices=Venta.CANAL_CHOICES, default='pos')
    direccion_id = serializers.PrimaryKeyRelatedField(queryset=Direccion.objects.all(), required=False)
    
    # Datos de los productos
    items = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField(),
            validators=[
                serializers.UniqueTogetherValidator(
                    queryset=DetalleVenta.objects.all(),
                    fields=['producto_id', 'cantidad']
                )
            ]
        )
    )

    # Datos del pago (Simplificado)
    metodo_pago = serializers.ChoiceField(choices=Pago.METODO_CHOICES)
    monto_pago = serializers.DecimalField(max_digits=10, decimal_places=2)
    referencia_pago = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
class AlertaSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para información de contexto
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    lote_numero = serializers.CharField(source='lote.numero_lote', read_only=True)
    
    class Meta:
        model = Alerta
        fields = [
            'id', 'tipo', 'mensaje', 'producto', 'producto_nombre',
            'lote', 'lote_numero', 'fecha_creacion', 'resuelto'
        ]
        read_only_fields = ['fecha_creacion']

    def validate(self, data):
        # Validación: Si es una alerta de lote, debe tener un lote asociado
        if data.get('tipo') in ['vencimiento'] and not data.get('lote'):
            raise serializers.ValidationError({
                "lote": "Las alertas de vencimiento deben estar asociadas a un lote específico."
            })
        
        # Validación: Si es una alerta de producto, debe tener un producto asociado
        if data.get('tipo') in ['stock_bajo', 'costo_alto'] and not data.get('producto'):
            raise serializers.ValidationError({
                "producto": "Las alertas de stock/costo deben estar asociadas a un producto."
            })
            
        return data
    
    
class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_info = serializers.CharField(source='producto.nombre', read_only=True)
    
    class Meta:
        model = ItemCarrito
        fields = ['id', 'producto', 'producto_info', 'cantidad']
        read_only_fields = ['id']

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a cero.")
        
        return value


class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True, source='itemcarrito_set')
    total_neto = serializers.SerializerMethodField()
    
    class Meta:
        model = Carrito
        # Incluir 'session_key' si es necesario para depuración de carritos anónimos
        fields = ['id', 'cliente', 'session_key', 'items', 'total_neto', 'creado', 'actualizado']
        read_only_fields = ['cliente', 'session_key', 'creado', 'actualizado']
        
    def get_total_neto(self, obj):
        # Calcula la suma total basada en los items
        total = 0
        for item in obj.items.all():
            total += item.cantidad * item.producto.precio_venta
        return total