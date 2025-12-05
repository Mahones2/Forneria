from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Producto, Lote, Venta, DetalleVenta, MovimientoInventario, Pago, Carrito

def procesar_venta(cliente, items_data, metodo_pago_info, canal='pos', direccion=None):
    """
    Procesa una venta completa con lógica FIFO para el inventario.
    
    Args:
        cliente (Cliente): Objeto cliente (puede ser None).
        items_data (list): Lista de dicts [{'producto_id': 1, 'cantidad': 5}, ...]
        metodo_pago_info (dict): {'metodo': 'DEB', 'monto': 10000, 'referencia': '1234'}
        canal (str): 'pos' o 'web'
        direccion (Direccion): Objeto direccion (opcional).
    
    Returns:
        Venta: La venta creada exitosamente.
    """
    
    # Iniciamos la transacción segura
    with transaction.atomic():
        
        # 1. Crear la cabecera de la Venta (aún con totales en 0)
        venta = Venta.objects.create(
            cliente=cliente,
            canal_venta=canal,
            direccion_despacho=direccion,
            estado='pagado', # Asumimos pago inmediato para este ejemplo
            fecha=timezone.now()
        )

        total_acumulado = 0
        
        # 2. Iterar sobre cada producto solicitado
        for item in items_data:
            producto_id = item['producto_id']
            cantidad_solicitada = int(item['cantidad'])
            
            # Bloqueamos el producto para que nadie más lo modifique mientras leemos
            # select_for_update() es vital en sistemas concurrentes
            try:
                producto = Producto.objects.select_for_update().get(id=producto_id)
            except Producto.DoesNotExist:
                raise ValidationError(f"El producto ID {producto_id} no existe.")

            # Validación rápida de stock global
            if producto.stock_fisico < cantidad_solicitada:
                raise ValidationError(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock_fisico}")

            # 3. Lógica FIFO: Buscar lotes y descontar
            # Buscamos lotes con stock > 0, ordenados por fecha de caducidad (el más viejo primero)
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
                    cantidad=-descuento_lote, # Negativo porque es salida
                    tipo='salida',
                    referencia=f"Venta #{venta.id}"
                )
                
                cantidad_pendiente -= descuento_lote

            # Doble chequeo de seguridad
            if cantidad_pendiente > 0:
                raise ValidationError(f"Inconsistencia de inventario en {producto.nombre}. Error crítico.")

            # 4. Crear el Detalle de Venta
            precio_final = producto.precio_venta # Aquí podrías aplicar descuentos por cliente
            subtotal = precio_final * cantidad_solicitada
            
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad_solicitada,
                precio_unitario=precio_final
            )
            
            total_acumulado += subtotal

        # 5. Finalizar Venta (Cálculo de impuestos)
        # Asumiendo IVA incluido en el precio de lista, desglosamos:
        # Precio = Neto * 1.19  => Neto = Precio / 1.19
        venta.total = total_acumulado
        venta.neto = total_acumulado / 1.19
        venta.iva = total_acumulado - venta.neto
        venta.save()

        # 6. Registrar el Pago
        Pago.objects.create(
            venta=venta,
            monto=metodo_pago_info['monto'],
            metodo=metodo_pago_info['metodo'],
            referencia_externa=metodo_pago_info.get('referencia', '')
        )
        
        return venta