from django.db.models import F, Sum, Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.db import transaction

# DRF Imports
from rest_framework import viewsets, permissions, status, generics
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

# Módulos Locales: Modelos
from .models import (
    Categoria, Nutricional, Lote, Producto, Alerta, Cliente, Direccion, Empleado, Turno,
    Carrito, ItemCarrito, Venta, DetalleVenta, Pago, MovimientoInventario,
    Ubicacion, Proveedor, Insumo, OrdenCompra, OrdenCompraItem, Etiqueta
)

# Módulos Locales: Serializers
from .serializers import (
    CategoriaSerializer, NutricionalSerializer, LoteSerializer, ProductoSerializer, 
    AlertaSerializer, ClienteSerializer, DireccionSerializer, 
    EmpleadoSerializer, EmpleadoCreateSerializer,
    TurnoSerializer, CarritoSerializer, ItemCarritoSerializer, VentaSerializer, 
    DetalleVentaSerializer, PagoSerializer, MovimientoInventarioSerializer,
    UbicacionSerializer, ProveedorSerializer, InsumoSerializer, OrdenCompraSerializer, 
    OrdenCompraItemSerializer, VentaInputSerializer, EtiquetaSerializer
)

# Módulos Locales: Servicios
from .services import procesar_venta


class EmpleadoDetailView(generics.RetrieveAPIView):
    serializer_class = EmpleadoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Devuelve el empleado asociado al usuario logeado
        return Empleado.objects.get(usuario=self.request.user)

# ==========================================
# PERMISOS CUSTOM
# ==========================================

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permite acceso de lectura a todos, pero solo el Cliente asociado al usuario
    puede editar/eliminar sus propios objetos.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        try:
            cliente_asociado = request.user.empleado.cliente 
        except (AttributeError, ObjectDoesNotExist):
            return False
        if hasattr(obj, 'cliente') and obj.cliente is not None:
            return obj.cliente == cliente_asociado
        return False

# ==========================================
# 1. CRUD BÁSICO DE ENTIDADES (API REST)
# ==========================================

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    # CAMBIO IMPORTANTE: Permitir acceso público para que el menú cargue sin login
    permission_classes = [AllowAny] 

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    # CAMBIO IMPORTANTE: Permitir acceso público para el catálogo
    permission_classes = [AllowAny]

class NutricionalViewSet(viewsets.ModelViewSet):
    queryset = Nutricional.objects.all()
    serializer_class = NutricionalSerializer
    permission_classes = [AllowAny]

class LoteViewSet(viewsets.ModelViewSet):
    queryset = Lote.objects.all()
    serializer_class = LoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Lote.objects.all()
        producto_id = self.request.query_params.get('producto')
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        return queryset

class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]

class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]

class ClienteViewSet(viewsets.ModelViewSet):
    # Usamos la lógica mejorada de tu compañera (ordenar por VIP/Compras)
    queryset = Cliente.objects.annotate(
        total_compras=Count('venta')
    ).order_by('-total_compras')
    
    serializer_class = ClienteSerializer
    # Permitimos acceso general para validar RUT en Kiosco, 
    # aunque idealmente esto debería ser IsAuthenticatedOrReadOnly
    permission_classes = [AllowAny]
    lookup_field = 'rut' 

    def get_queryset(self):
        queryset = super().get_queryset()
        rut_param = self.request.query_params.get('rut', None)
        nombre_param = self.request.query_params.get('nombre', None)

        if rut_param:
            queryset = queryset.filter(rut__icontains=rut_param)
        if nombre_param:
            queryset = queryset.filter(nombre__icontains=nombre_param)
        return queryset

    def _get_ventas_data(self, cliente):
        ventas = Venta.objects.filter(cliente=cliente).prefetch_related('detalles__producto').order_by('-fecha')
        ventas_data = []
        for venta in ventas:
            productos = []
            for detalle in venta.detalles.all():
                subtotal = detalle.cantidad * detalle.precio_unitario 
                productos.append({
                    'id': detalle.producto.id,
                    'nombre': detalle.producto.nombre,
                    'cantidad': detalle.cantidad,
                    'precio_unitario': str(detalle.precio_unitario),
                    'subtotal': str(subtotal),
                })
            ventas_data.append({
                'id': venta.id,
                'fecha': venta.fecha,
                'total': str(venta.total),
                'estado': venta.estado,
                'folio_documento': venta.folio_documento,
                'productos': productos
            })
        return ventas_data

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object() 
        except ObjectDoesNotExist:
            return Response({"detail": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        response_data = serializer.data
        response_data['ventas'] = self._get_ventas_data(instance)
        return Response(response_data)

    @action(detail=False, methods=['get'])
    def buscar_por_rut(self, request):
        rut_param = request.query_params.get('rut')
        if not rut_param:
            return Response({"error": "Debe proporcionar el parámetro 'rut'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cliente = Cliente.objects.get(rut=rut_param)
        except Cliente.DoesNotExist:
            return Response({"error": f"Cliente con RUT {rut_param} no encontrado."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = self.get_serializer(cliente)
        response_data = serializer.data
        response_data['ventas'] = self._get_ventas_data(cliente)
        return Response(response_data)


# Versión Segura y Correcta de EmpleadoViewSet
class EmpleadoViewSet(viewsets.ModelViewSet):
    queryset = Empleado.objects.all().order_by('usuario__first_name', 'usuario__last_name')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return EmpleadoCreateSerializer
        return EmpleadoSerializer

    def get_permissions(self):
        from rest_framework.permissions import BasePermission

        class IsAdminOnly(BasePermission):
            def has_permission(self, request, view):
                if request.method in ('GET', 'HEAD', 'OPTIONS'):
                    return request.user and request.user.is_authenticated
                try:
                    cargo = getattr(request.user.empleado, 'cargo', None)
                except Exception:
                    cargo = None
                return bool(request.user and request.user.is_authenticated and (request.user.is_superuser or cargo == 'Administrador'))

        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminOnly()]

    def perform_destroy(self, instance):
        user = instance.usuario
        instance.delete()
        if user:
            user.delete()

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        try:
            cargo = getattr(request.user.empleado, 'cargo', None)
        except Exception:
            cargo = None
        if not (request.user.is_superuser or cargo == 'Administrador'):
            return Response({'detail': 'Sin permisos'}, status=status.HTTP_403_FORBIDDEN)

        empleado = self.get_object()
        new_password = request.data.get('password')
        if not new_password or len(new_password) < 6:
            return Response({'password': ['La contraseña debe tener al menos 6 caracteres']}, status=status.HTTP_400_BAD_REQUEST)
        empleado.usuario.set_password(new_password)
        empleado.usuario.save(update_fields=['password'])
        return Response({'detail': 'Contraseña actualizada'})


class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer
    permission_classes = [IsAuthenticated]

class UbicacionViewSet(viewsets.ModelViewSet):
    queryset = Ubicacion.objects.all()
    serializer_class = UbicacionSerializer
    permission_classes = [IsAuthenticated]

class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated]

class InsumoViewSet(viewsets.ModelViewSet):
    queryset = Insumo.objects.all()
    serializer_class = InsumoSerializer
    permission_classes = [IsAuthenticated]

class OrdenCompraViewSet(viewsets.ModelViewSet):
    queryset = OrdenCompra.objects.all()
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated]

class OrdenCompraItemViewSet(viewsets.ModelViewSet):
    queryset = OrdenCompraItem.objects.all()
    serializer_class = OrdenCompraItemSerializer
    permission_classes = [IsAuthenticated]

# ==========================================
# 2. VISTAS CON LÓGICA DE NEGOCIO
# ==========================================

class DireccionViewSet(viewsets.ModelViewSet):
    serializer_class = DireccionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Direccion.objects.all()
        try:
            cliente = user.empleado.cliente 
            return Direccion.objects.filter(cliente=cliente)
        except (AttributeError, ObjectDoesNotExist):
            raise PermissionDenied("Acceso denegado. No tienes permisos para ver direcciones.")

    def perform_create(self, serializer):
        user = self.request.user
        try:
            cliente = user.empleado.cliente
            serializer.save(cliente=cliente)
        except (AttributeError, ObjectDoesNotExist):
            if self.request.data.get('cliente'):
                 serializer.save() 
            else:
                raise PermissionDenied("Para crear una dirección sin perfil de Cliente, debe especificar 'cliente' en los datos.")
        
class CarritoViewSet(viewsets.ModelViewSet):
    queryset = ItemCarrito.objects.all() 
    serializer_class = ItemCarritoSerializer
    permission_classes = [AllowAny] 

    def get_carrito(self):
        user = self.request.user
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.save()
            session_key = self.request.session.session_key

        carrito = None
        if user.is_authenticated and hasattr(user, 'empleado'):
            try:
                cliente = user.empleado.cliente
                carrito, created = Carrito.objects.get_or_create(cliente=cliente)
                # Migración de carrito anónimo
                ses_carrito = Carrito.objects.filter(session_key=session_key, cliente__isnull=True).first()
                if ses_carrito and ses_carrito.id != carrito.id:
                    ItemCarrito.objects.filter(carrito=ses_carrito).update(carrito=carrito)
                    ses_carrito.delete()
            except Exception:
                pass 

        if not carrito:
            carrito, created = Carrito.objects.get_or_create(session_key=session_key, cliente__isnull=True)
        return carrito

    def get_queryset(self):
        carrito = self.get_carrito()
        return ItemCarrito.objects.filter(carrito=carrito).order_by('id')

    def perform_create(self, serializer):
        carrito = self.get_carrito()
        producto_id = self.request.data.get('producto')
        cantidad = serializer.validated_data.get('cantidad', 1)

        item_existente = ItemCarrito.objects.filter(carrito=carrito, producto_id=producto_id).first()
        if item_existente:
            item_existente.cantidad += cantidad
            item_existente.save()
            return Response(ItemCarritoSerializer(item_existente).data, status=status.HTTP_200_OK)
        else:
            serializer.save(carrito=carrito)
            
    @action(detail=False, methods=['delete'])
    def vaciar(self, request):
        carrito = self.get_carrito()
        carrito.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        carrito = self.get_carrito()
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)
        
class ItemCarritoViewSet(viewsets.ModelViewSet):
    queryset = ItemCarrito.objects.all() 
    serializer_class = ItemCarritoSerializer
    permission_classes = [IsAuthenticated] 

class ProductosStockBajoList(generics.ListAPIView):
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        return Producto.objects.filter(stock_fisico__lte=F('stock_minimo_global'))

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = VentaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        items_data = data.pop('items')
        pagos_info = data.pop('pagos')
        
        try:
            cliente_obj = Cliente.objects.get(id=data.get('cliente_id')) if data.get('cliente_id') else None
            direccion_obj = Direccion.objects.get(id=data.get('direccion_id')) if data.get('direccion_id') else None
            
            venta_creada = procesar_venta(
                cliente=cliente_obj,
                direccion=direccion_obj,
                items_data=items_data,
                metodo_pago_info=pagos_info,
                usuario=request.user, 
                canal=data.get('canal', 'pos'),
            )
            
            respuesta_serializer = VentaSerializer(venta_creada)
            return Response(respuesta_serializer.data, status=status.HTTP_201_CREATED)
            
        except Cliente.DoesNotExist:
            return Response({'error': 'Cliente no encontrado.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # --- MONITOR DE COCINA ---
    @action(detail=False, methods=['get'])
    def tablero_pedidos(self, request):
        hoy = timezone.now().date()
        pendientes_qs = Venta.objects.filter(estado='pagado').order_by('fecha', 'id')
        terminados_qs = Venta.objects.filter(
            estado__in=['entregado', 'en_camino'],
            fecha__date=hoy
        ).order_by('-id')

        data = {
            "pendientes": VentaSerializer(pendientes_qs, many=True).data,
            "terminados": VentaSerializer(terminados_qs, many=True).data
        }
        return Response(data)

    @action(detail=True, methods=['post'])
    def marcar_entregado(self, request, pk=None):
        venta = self.get_object()
        try:
            if hasattr(venta, 'marcar_entregado'):
                venta.marcar_entregado()
            else:
                venta.estado = 'entregado'
                venta.save()
            return Response({'status': 'pedido listo', 'nuevo_estado': venta.estado})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DetalleVentaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DetalleVenta.objects.all() 
    serializer_class = DetalleVentaSerializer
    permission_classes = [IsAuthenticated]

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    
class VentaCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = VentaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        items_data = data.pop('items')
        pagos_info = data.pop('pagos')
        
        try:
            cliente_obj = Cliente.objects.get(id=data.get('cliente_id')) if data.get('cliente_id') else None
            direccion_obj = Direccion.objects.get(id=data.get('direccion_id')) if data.get('direccion_id') else None
            
            venta_creada = procesar_venta(
                cliente=cliente_obj,
                direccion=direccion_obj,
                items_data=items_data,
                metodo_pago_info=pagos_info,
                usuario=request.user, 
                canal=data.get('canal', 'pos'),
            )
            
            respuesta_serializer = VentaSerializer(venta_creada)
            return Response(respuesta_serializer.data, status=status.HTTP_201_CREATED)
            
        except Cliente.DoesNotExist:
            return Response({'error': 'Cliente no encontrado.'}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Error interno: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==========================================
# 3. VISTAS PÚBLICAS Y KIOSCO
# ==========================================

class CatalogoUnificadoView(APIView):
    permission_classes = [AllowAny] 

    def get(self, request):
        categorias = Categoria.objects.all()
        productos = Producto.objects.all()
        data = {
            "categorias": CategoriaSerializer(categorias, many=True).data,
            "productos": ProductoSerializer(productos, many=True).data
        }
        return Response(data)

class KioscoViewSet(viewsets.ViewSet):
    # Acceso público para que los clientes puedan pedir sin login
    permission_classes = [AllowAny] 

    @action(detail=False, methods=['get'])
    def catalogo(self, request):
        categorias = Categoria.objects.all()
        productos = Producto.objects.filter(stock_fisico__gt=0).select_related('categoria')
        return Response({
            "categorias": CategoriaSerializer(categorias, many=True).data,
            "productos": ProductoSerializer(productos, many=True).data
        })

    @action(detail=False, methods=['get'])
    def validar_cliente(self, request):
        rut = request.query_params.get('rut')
        try:
            cliente = Cliente.objects.get(rut=rut)
            return Response({
                "existe": True,
                "id": cliente.id,
                "nombre": cliente.nombre,
                "rut": cliente.rut
            })
        except Cliente.DoesNotExist:
            return Response({"existe": False}, status=200)

    @action(detail=False, methods=['post'])
    def registrar_cliente(self, request):
        serializer = ClienteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['post'])
    def crear_pedido(self, request):
        data = request.data
        
        items_data = data.get('items', [])
        pagos_info = data.get('pagos', [])
        cliente_id = data.get('cliente_id')
        fecha_entrega = data.get('fecha_entrega') 

        try:
            # 1. Búsqueda SEGURA del cliente
            cliente_obj = None
            if cliente_id:
                cliente_obj = Cliente.objects.get(id=cliente_id)

            # 2. Crear la venta 
            venta_creada = procesar_venta(
                cliente=cliente_obj,
                items_data=items_data,
                metodo_pago_info=pagos_info,
                usuario=None, # Kiosco es usuario anónimo
                canal='web',
                direccion=None
            )

            # 3. Guardar fecha de entrega si existe
            if fecha_entrega:
                venta_creada.fecha_entrega = fecha_entrega
                venta_creada.save(update_fields=['fecha_entrega'])

            return Response({
                "id": venta_creada.id, 
                "total": venta_creada.total,
                "mensaje": "Pedido recibido"
            }, status=201)

        except Cliente.DoesNotExist:
             return Response({'error': 'Cliente indicado no existe'}, status=400)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            # Error interno
            print(f"Error Kiosco: {e}")
            return Response({'error': 'Error interno procesando el pedido.'}, status=500)

# ==========================================
# 4. VISTAS TRADICIONALES (Django View)
# ==========================================

def finalizar_compra_view(request):
    """
    Vista tradicional para E-commerce (NO DRF/API).
    """
    if request.method == 'POST':
        try:
            carrito = Carrito.objects.get(session_key=request.session.session_key)
            items = []
            total_carrito = 0
            for item in carrito.items.all():
                items.append({'producto_id': item.producto.id, 'cantidad': item.cantidad})
                total_carrito += item.subtotal()
            
            pagos_info = {
                'metodo': request.POST.get('metodo_pago'), 
                'monto': total_carrito,
                'referencia': request.POST.get('referencia_pago', 'N/A') 
            }
            
            venta_creada = procesar_venta(
                cliente=carrito.cliente,
                items_data=items,
                metodo_pago_info=pagos_info,
                usuario=request.user if request.user.is_authenticated else None,
                canal='web'
            )
            
            carrito.delete()
            return JsonResponse({'status': 'ok', 'venta_id': venta_creada.id})

        except Carrito.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'Carrito vacío o sesión expirada'}, status=400)
        except ValidationError as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': 'Error interno de procesamiento.'}, status=500)

class EtiquetaViewSet(viewsets.ModelViewSet):
    queryset = Etiqueta.objects.all()
    serializer_class = EtiquetaSerializer
    permission_classes = [IsAuthenticated]