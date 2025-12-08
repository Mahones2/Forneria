from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Producto, Lote, Venta, DetalleVenta, MovimientoInventario, Pago

def procesar_venta(cliente, items_data, metodo_pago_info, usuario=None, canal='pos', direccion=None):
    """
    Procesa una venta completa con lógica FIFO para el inventario y pagos múltiples.
    
    Args:
        cliente (Cliente): Objeto cliente (puede ser None).
        items_data (list): Lista [{'producto_id': 1, 'cantidad': 5}, ...]
        metodo_pago_info (list): Lista de pagos: [{'metodo': 'DEB', 'monto': 10000, 'monto_recibido': 10000}, ...]
        usuario (User): El usuario (empleado) que realiza la venta (para trazabilidad).
        canal (str): 'pos' o 'web'
        direccion (Direccion): Objeto direccion (opcional).
    """
    
    # Iniciamos la transacción segura
    with transaction.atomic():
        
        # 1. Crear la cabecera de la Venta
        empleado = None
        if usuario and hasattr(usuario, 'empleado'):
            empleado = usuario.empleado

        venta = Venta.objects.create(
            cliente=cliente,
            empleado=empleado,
            canal_venta=canal,
            direccion_despacho=direccion,
            estado='pagado', 
            fecha=timezone.now()
        )

        total_acumulado = Decimal(0)
        
        # 2. Iterar sobre cada producto solicitado y 3. Lógica FIFO
        for item in items_data:
            producto_id = item['producto_id']
            cantidad_solicitada = int(item['cantidad'])
            
            # Bloqueamos el producto para lectura segura
            try:
                producto = Producto.objects.select_for_update().get(id=producto_id)
            except Producto.DoesNotExist:
                raise ValidationError(f"El producto ID {producto_id} no existe.")

            # Validación de stock global (leemos el campo optimizado)
            if producto.stock_fisico < cantidad_solicitada:
                raise ValidationError(f"Stock insuficiente para {producto.nombre}. Solicitado: {cantidad_solicitada}, Disponible: {producto.stock_fisico}")

            # Lógica FIFO: Buscar lotes y descontar
            lotes = Lote.objects.filter(
                producto=producto, 
                stock_actual__gt=0,
                eliminado__isnull=True
            ).order_by('fecha_caducidad').select_for_update()

            cantidad_pendiente = cantidad_solicitada
            
            for lote in lotes:
                if cantidad_pendiente <= 0:
                    break
                
                # Cuánto sacamos de este lote específico
                descuento_lote = min(cantidad_pendiente, lote.stock_actual)
                
                # Actualizar el lote
                lote.stock_actual -= descuento_lote
                lote.save() 
                
                # Registrar el movimiento (Trazabilidad)
                MovimientoInventario.objects.create(
                    producto=producto,
                    lote=lote,
                    cantidad=-descuento_lote, # Negativo es salida
                    tipo='salida',
                    referencia=f"Venta #{venta.id}",
                    usuario=usuario
                )
                
                cantidad_pendiente -= descuento_lote

            # Doble chequeo de seguridad
            if cantidad_pendiente > 0:
                raise ValidationError(f"Error de integridad: El stock global decía que había, pero los lotes no sumaron lo suficiente para {producto.nombre}.")

            # 4. Crear el Detalle de Venta
            precio_final = producto.precio_venta 
            subtotal = precio_final * Decimal(cantidad_solicitada)
            
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad_solicitada,
                precio_unitario=precio_final,
                descuento=0 
            )
            
            total_acumulado += subtotal

        # 5. Finalizar Venta (Cálculo de impuestos con Decimal)
        factor_iva = Decimal('1.19')
        
        venta.total = total_acumulado
        venta.neto = total_acumulado / factor_iva
        venta.iva = total_acumulado - venta.neto
        venta.save()

       
        for pago_data in metodo_pago_info:
            
            # Usamos .get() para campos opcionales como 'monto_recibido' y 'referencia'
            monto_recibido = pago_data.get('monto_recibido') or pago_data['monto']
            referencia = pago_data.get('referencia', '')
            
            Pago.objects.create(
                venta=venta,
                monto=Decimal(pago_data['monto']),
                metodo=pago_data['metodo'],
                monto_recibido=Decimal(monto_recibido), # Añadido el campo si existe en tu modelo Pago
                referencia_externa=referencia
            )
        
        return venta