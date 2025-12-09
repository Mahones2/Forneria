from rest_framework import serializers
from .models import * 
from datetime import date, datetime
from django.db.models import Sum
import re

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'
            

class NutricionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nutricional
        fields = '__all__'
    def validate_calorias(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Las calorias no pueden ser negativas.")
        return value
    def validate_proteinas(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Las proteinas no pueden ser negativas.")
        return value
    def validate_grasas(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Las grasas no pueden ser negativas.")
        return value
    def validate_carbohidratos(self, value):
        if value is not None and value< 0:
            raise serializers.ValidationError("Las hidratos de carbono no pueden ser negativas.")
        return value
    def validate_azucares(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Las azúcares no pueden ser negativas.")
        return value
    def validate_sodio(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Las sodio no pueden ser negativas.")
        return value

class LoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lote
        fields = [
            'id', 'numero_lote', 'fecha_elaboracion', 'fecha_caducidad',
            'stock_actual', 'stock_minimo', 'stock_maximo', 'producto' 
        ]
        read_only_fields = ['id']
    def validate(self, data):
        # Validación de fechas
        if data.get("fecha_elaboracion") and data.get("fecha_caducidad"):
            if data["fecha_caducidad"] <= data["fecha_elaboracion"]:
                raise serializers.ValidationError({
                    "fecha_caducidad": "La fecha de caducidad debe ser posterior a la fecha de elaboración."
                })

        # Validación de stock
        if data.get("stock_actual") is not None and data["stock_actual"] < 0:
            raise serializers.ValidationError({
                "stock_actual": "El stock actual no puede ser negativo."
            })
        if data.get("stock_minimo") is not None and data["stock_minimo"] < 0:
            raise serializers.ValidationError({
                "stock_minimo": "El stock mínimo no puede ser negativo."
            })
        if data.get("stock_maximo") is not None and data["stock_maximo"] < 0:
            raise serializers.ValidationError({
                "stock_maximo": "El stock máximo no puede ser negativo."
            })

        if (
            data.get("stock_minimo") is not None
            and data.get("stock_maximo") is not None
            and data.get("stock_actual") is not None
        ):
            if data["stock_minimo"] > data["stock_maximo"]:
                raise serializers.ValidationError({
                    "stock_minimo": "El stock mínimo no puede ser mayor que el stock máximo."
                })
            if not (data["stock_minimo"] <= data["stock_actual"] <= data["stock_maximo"]):
                raise serializers.ValidationError({
                    "stock_actual": "El stock actual debe estar entre el mínimo y el máximo definidos."
                })

        # Validación de caducidad en el pasado
        if data.get("fecha_caducidad") and data["fecha_caducidad"] < date.today():
            raise serializers.ValidationError({
                "fecha_caducidad": "La fecha de caducidad no puede estar en el pasado."
            })

        return data


# --- Producto Serializer ---
class ProductoSerializer(serializers.ModelSerializer):
    nutricional = NutricionalSerializer(read_only=True)
    lotes = LoteSerializer(many=True, required=False)
    stock_total = serializers.SerializerMethodField() 

    class Meta:
        model = Producto
        fields = '__all__'  

    def get_stock_total(self, obj):
        return obj.lotes.aggregate(total_stock=Sum('stock_actual'))['total_stock'] or 0

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0.")
        return value

    def create(self, validated_data):
         lotes_data = validated_data.pop('lotes', [])
         producto = Producto.objects.create(**validated_data)
         for lote_data in lotes_data:
             Lote.objects.create(producto=producto, **lote_data)
         return producto

    def update(self, instance, validated_data):
        lotes_data = validated_data.pop('lotes', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if lotes_data is not None:
             instance.lotes.all().delete()
             for lote_data in lotes_data:
                 Lote.objects.create(producto=instance, **lote_data)
                 
        return super().update(instance, validated_data)


class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerta
        fields = '__all__'

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'
    
    def validate_rut(self, value):
        if not value:
            raise serializers.ValidationError("El RUT es obligatorio.")

        # Validar formato: 7 u 8 dígitos + guion + dígito verificador (número o K)
        patron = r'^\d{7,8}-[\dkK]$'
        if not re.match(patron, value):
            raise serializers.ValidationError("El RUT debe tener el formato 12345678-5")

        return value

    
class DetalleVentaSerializer(serializers.ModelSerializer):
    
    producto_info = ProductoSerializer(source='producto', read_only=True)
    
    class Meta:
        model = DetalleVenta
        fields = '__all__'
        
    # Las validaciones de cantidad, precio y descuento son excelentes y se mantienen.
    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return value

    def validate_precio_unitario(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio unitario debe ser mayor a 0.")
        return value

    def validate_descuento_pct(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("El descuento debe estar entre 0 y 100%.")
        return value

    def validate(self, data):
        # Tu validación cruzada es correcta y se mantiene.
        if data.get("descuento_pct") is not None:
            precio_final = data["precio_unitario"] * (1 - data["descuento_pct"] / 100)
            if precio_final < 0:
                raise serializers.ValidationError({
                    "precio_unitario": "El precio final no puede ser negativo."
                })
        return data

# TEMPORALMENTE COMENTADO - Modelo Pago no existe
# class PagoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Pago
#         fields = '__all__'
#     def validate_monto(self, value):
#         if value <= 0:
#             raise serializers.ValidationError("El monto del pago debe ser positivo.")
#         return value
        
class VentaSerializer(serializers.ModelSerializer):
    cliente_rut = serializers.CharField(write_only=True, required=False)

    # Relaciones anidadas
    detalles = DetalleVentaSerializer(many=True)
    # pagos = PagoSerializer(many=True, required=False)  # COMENTADO - Modelo Pago no existe

    # Campo calculado para el estado de pago - COMENTADO
    # total_pagado = serializers.SerializerMethodField()
    # saldo_pendiente = serializers.SerializerMethodField()
    
    class Meta:
        model = Venta
        fields = [
             'id', 'fecha', 'total_sin_iva', 'total_iva', 'descuento',
             'total_con_iva', 'canal_venta', 'folio',
             'cliente', 'cliente_rut', 'empleado',
             'detalles'  # , 'pagos', 'total_pagado', 'saldo_pendiente'  # COMENTADO
         ]
        read_only_fields = ['cliente', 'empleado']  # , 'total_pagado', 'saldo_pendiente'  # COMENTADO
        
        cliente_rut = serializers.CharField(write_only=True, required=False)
        
    # COMENTADO - Modelo Pago no existe
    # def get_total_pagado(self, obj):
    #      return obj.pagos.aggregate(total=Sum('monto'))['total'] or 0

    # def get_saldo_pendiente(self, obj):
    #     total_pagado = self.get_total_pagado(obj)
    #     return obj.total_con_iva - total_pagado
        
    def create(self, validated_data):
        rut = validated_data.pop('cliente_rut', None)
        if rut:
            cliente, created = Cliente.objects.get_or_create(
                rut=rut,
                defaults={
                    "nombre": None,
                    "correo": None
                }
            )
            validated_data['cliente'] = cliente
        return super().create(validated_data)
        
    def validate(self, data):
        # total_con_iva = total_sin_iva + total_iva - descuento
        esperado = data["total_sin_iva"] + data["total_iva"] - data["descuento"]
        esperado = data["total_sin_iva"] + data["total_iva"] - data["descuento"]
        if data["total_con_iva"] != esperado:
             raise serializers.ValidationError({"total_con_iva": "El total con IVA no coincide con el cálculo esperado."})

        # Validación: fecha no puede ser futura
        if data.get("fecha") and data["fecha"].date() > date.today():
            raise serializers.ValidationError({
                "fecha": "La fecha de la venta no puede estar en el futuro."
            })

        return data
        
        
        
class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = '__all__'
    def validate(self, data):
        # Validar que la fecha no sea futura
        if data.get("fecha") and data["fecha"] > datetime.now():
            raise serializers.ValidationError({
                "fecha": "La fecha del movimiento no puede estar en el futuro."
            })

        # Validar coherencia de tipo de movimiento
        if data["tipo_movimiento"] == "salida":
            # Validar contra stock actual del producto
            if data["cantidad"] > data["producto"].stock_actual:
                raise serializers.ValidationError({
                    "cantidad": "No puedes retirar más cantidad que el stock disponible."
                })

        return data
class EmpleadoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = Empleado
        fields = [
            'id', 'run', 'fono', 'direccion', 'cargo', 
            'usuario', 'nombre_completo'
        ]
        
    def validate_run(self, value):
        if not value:
            raise serializers.ValidationError("El RUN es obligatorio.")
        return value

    def validate_fono(self, value):
        if not value:
            raise serializers.ValidationError("El número de teléfono es obligatorio.")
        
        return value
        
    def validate_usuario(self, value):
        if value is None:
            raise serializers.ValidationError("Debe asociar un usuario de sistema válido.")
        return value

    def create(self, validated_data):
        return super().create(validated_data)
    
class TurnoSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.__str__', read_only=True)
    
    class Meta:
        model = Turno
        fields = '__all__'