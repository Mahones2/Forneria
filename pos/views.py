from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator # No usada, pero mantenida si se necesita en otras vistas.
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db.models import Prefetch

# DRF Imports
from rest_framework import viewsets, permissions, status, generics
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

# Filtrado (Necesario si se usara DetalleVentaViewSet para filtrado por ID de Venta)
from django_filters.rest_framework import DjangoFilterBackend 

# Módulos Locales: Modelos
from .models import (
    Categoria, Nutricional, Lote, Producto, Alerta, Cliente, Direccion, Empleado, Turno,
    Carrito, ItemCarrito, Venta, DetalleVenta, Pago, MovimientoInventario,
    Ubicacion, Proveedor, Insumo, OrdenCompra, OrdenCompraItem
)

# Módulos Locales: Serializers (Asegúrate de que VentaInputSerializer existe en serializers.py)
from .serializers import (
    CategoriaSerializer, NutricionalSerializer, LoteSerializer, ProductoSerializer, 
    AlertaSerializer, ClienteSerializer, DireccionSerializer, EmpleadoSerializer, 
    TurnoSerializer, CarritoSerializer, ItemCarritoSerializer, VentaSerializer, 
    DetalleVentaSerializer, PagoSerializer, MovimientoInventarioSerializer,
    UbicacionSerializer, ProveedorSerializer, InsumoSerializer, OrdenCompraSerializer, 
    OrdenCompraItemSerializer, VentaInputSerializer 
)

# Módulos Locales: Servicios
from .services import procesar_venta


class EmpleadoDetailView(generics.RetrieveAPIView):
    serializer_class = EmpleadoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # devuelve el empleado asociado al usuario logeado
        return Empleado.objects.get(usuario=self.request.user)

# ==========================================
# PERMISOS
# ==========================================


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permite acceso de lectura a todos, pero solo el Cliente asociado al usuario
    puede editar/eliminar sus propios objetos (ej. Direccion).
    """
    
    def has_object_permission(self, request, view, obj):
        # Permite GET, HEAD, OPTIONS (métodos seguros) a cualquiera
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # La escritura (PUT, PATCH, DELETE) requiere autenticación
        if not request.user.is_authenticated:
            return False
            
        # 1. Intentamos obtener el Cliente asociado al usuario logueado
        try:
            # Asumimos la ruta de asociación: request.user -> Empleado -> Cliente
            cliente_asociado = request.user.empleado.cliente 
        except (AttributeError, ObjectDoesNotExist):
            # Si el usuario no es un empleado o el empleado no tiene cliente asociado, denegar.
            # (Esto maneja Superusuarios o Usuarios sin perfil completo)
            return False
            
        # 2. Comparamos el objeto con el Cliente asociado
        # Asume que el objeto (obj) tiene un campo 'cliente' (ej. obj.cliente)
        # Esto es válido para Direccion y probablemente Carrito/Venta (si no apuntan a User).
        if hasattr(obj, 'cliente') and obj.cliente is not None:
            return obj.cliente == cliente_asociado
            
        return False

# ==========================================
# 1. CRUD BÁSICO DE ENTIDADES (API REST)
# ==========================================

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated] 

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

class NutricionalViewSet(viewsets.ModelViewSet):
    queryset = Nutricional.objects.all()
    serializer_class = NutricionalSerializer
    permission_classes = [IsAuthenticated]

class LoteViewSet(viewsets.ModelViewSet):
    queryset = Lote.objects.all()
    serializer_class = LoteSerializer
    permission_classes = [IsAuthenticated]

class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]

class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import ObjectDoesNotExist
# Asegúrate de que todos los modelos y serializers necesarios estén importados
# from .models import Cliente, Venta, DetalleVenta 
# from .serializers import ClienteSerializer, VentaSerializer # Usaremos solo ClienteSerializer y el formato manual
from decimal import Decimal # Necesario si vas a usar Decimal en la lógica

# Tu ClienteSerializer debería ser:
# class ClienteSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Cliente
#         fields = '__all__'


class ClienteViewSet(viewsets.ModelViewSet):
    # La lista por defecto (usada en get_queryset si no hay filtros)
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Permite buscar, actualizar y eliminar por el campo 'rut' (GET /clientes/{rut}/)
    lookup_field = 'rut' 

    # ----------------------------------------------------
    # 1. OPTIMIZACIÓN Y FILTRADO PARA LISTADO (GET /clientes/)
    # ----------------------------------------------------

    def get_queryset(self):
        """
        Retorna la lista de clientes. Permite filtrar opcionalmente por 'rut' y 'nombre'.
        Ignora los parámetros de búsqueda si están vacíos, devolviendo la lista completa.
        """
        queryset = Cliente.objects.all().order_by('nombre')
        
        # Obtener parámetros de la URL
        rut_param = self.request.query_params.get('rut', None)
        nombre_param = self.request.query_params.get('nombre', None)

        # Aplicar filtro SÓLO si el parámetro tiene contenido real
        if rut_param:
            # __icontains permite búsqueda parcial insensible a mayúsculas/minúsculas
            queryset = queryset.filter(rut__icontains=rut_param)
        
        if nombre_param:
            queryset = queryset.filter(nombre__icontains=nombre_param)
            
        return queryset

    # ----------------------------------------------------
    # 2. MÉTODO AUXILIAR PARA OBTENER VENTAS (Reutilizable y Limpio)
    # ----------------------------------------------------

    def _get_ventas_data(self, cliente):
        """
        Método auxiliar para obtener y formatear los datos de las ventas 
        de un cliente específico.
        """
        # Optimizado: Usa prefetch_related para cargar todos los detalles y productos 
        # en pocas consultas.
        ventas = Venta.objects.filter(cliente=cliente).prefetch_related('detalles__producto').order_by('-fecha')
        
        ventas_data = []
        for venta in ventas:
            productos = []
            
            for detalle in venta.detalles.all():
                # Asegura que la multiplicación y la conversión a string usen Decimal
                # Se asume que DetalleVenta.cantidad y DetalleVenta.precio_unitario son DecimalFields
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


    # ----------------------------------------------------
    # 3. MÉTODO RETRIEVE (GET /clientes/{rut}/)
    # ----------------------------------------------------

    def retrieve(self, request, *args, **kwargs):
        """
        Retorna el cliente encontrado por 'rut' con sus ventas asociadas 
        y los productos de cada venta.
        """
        try:
            # get_object() ya usa lookup_field='rut' para buscar
            instance = self.get_object() 
        except ObjectDoesNotExist:
            return Response({"detail": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # Serializa los datos básicos del cliente
        serializer = self.get_serializer(instance)
        response_data = serializer.data
        
        # Agrega las ventas detalladas usando el método auxiliar
        response_data['ventas'] = self._get_ventas_data(instance)
        
        return Response(response_data)

    # ----------------------------------------------------
    # 2. ACCIÓN ADICIONAL (Opcional, si necesitas la ruta específica)
    # ----------------------------------------------------

    @action(detail=False, methods=['get'])
    def buscar_por_rut(self, request):
        """
        Busca un cliente por su RUT pasado como parámetro de consulta (query parameter).
        Endpoint: GET /pos/api/clientes/buscar_por_rut/?rut=12345678-9
        """
        rut_param = request.query_params.get('rut')
        
        if not rut_param:
            return Response({"error": "Debe proporcionar el parámetro 'rut'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Buscar el cliente directamente
            cliente = Cliente.objects.get(rut=rut_param)
        except Cliente.DoesNotExist:
            return Response({"error": f"Cliente con RUT {rut_param} no encontrado."}, status=status.HTTP_404_NOT_FOUND)
            
        # Serializa los datos básicos del cliente
        serializer = self.get_serializer(cliente)
        response_data = serializer.data
        
        # Agrega las ventas detalladas
        response_data['ventas'] = self._get_ventas_data(cliente)
        
        return Response(response_data)

class EmpleadoViewSet(viewsets.ModelViewSet):
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer
    permission_classes = [IsAuthenticated]

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
# 2. VISTAS CON LÓGICA DE NEGOCIO Y PERMISOS
# ==========================================

class DireccionViewSet(viewsets.ModelViewSet):
    """
    CRUD para las direcciones de un cliente, restringido al dueño.
    """
    serializer_class = DireccionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        """
        Devuelve todas las direcciones para administradores/superusuarios, 
        o solo las direcciones del cliente asociado al usuario logueado.
        """
        user = self.request.user
        
        # 1. Permiso para Superusuarios o Administradores (deben tener un campo 'cargo' o 'is_superuser')
        if user.is_superuser: # Si es superusuario, ve todas
            return Direccion.objects.all()
        
        # 2. Búsqueda de la asociación Cliente
        try:
            # Asumimos que el User tiene un Empleado, y ese Empleado tiene un Cliente asociado
            # (Esto sigue siendo una asunción muy fuerte para un negocio POS/E-commerce)
            cliente = user.empleado.cliente 
            return Direccion.objects.filter(cliente=cliente)
            
        except (AttributeError, ObjectDoesNotExist):
            # Si no hay asociación clara (ni superuser ni cliente asociado), denegar el listado
            raise PermissionDenied("Acceso denegado. No tienes permisos para ver direcciones.")

    def perform_create(self, serializer):
        """Asigna automáticamente el cliente logueado a la nueva dirección."""
        user = self.request.user
        
        try:
            # Asignar la dirección al cliente asociado al empleado que la está creando
            cliente = user.empleado.cliente
            serializer.save(cliente=cliente)
        except (AttributeError, ObjectDoesNotExist):
            # Si un Administrador está creando una dirección para un cliente X, 
            # debería validar que el 'cliente_id' esté en la data, o denegar.
            if self.request.data.get('cliente'):
                 # Si se pasa el ID del cliente en la data, permite que el Admin lo cree
                 serializer.save() 
            else:
                raise PermissionDenied("Para crear una dirección sin perfil de Cliente, debe especificar 'cliente' en los datos.")
        
class CarritoViewSet(viewsets.ModelViewSet):
    """
    Gestión de los items dentro del Carrito de Compra (E-commerce).
    Este ViewSet gestiona los Ítems (ItemCarrito) y no el Carrito padre.
    """
    # IMPORTANTE: Definir queryset base para el Router y serializer para listar
    queryset = ItemCarrito.objects.all() 
    serializer_class = ItemCarritoSerializer
    permission_classes = [permissions.AllowAny] 

    def get_carrito(self):
        """Obtiene o crea el carrito activo para el usuario/sesión."""
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
            # Caso anónimo
            carrito, created = Carrito.objects.get_or_create(session_key=session_key, cliente__isnull=True)
            
        return carrito

    def get_queryset(self):
        """Filtra los items para mostrar solo el contenido del carrito activo."""
        carrito = self.get_carrito()
        return ItemCarrito.objects.filter(carrito=carrito).order_by('id')

    def perform_create(self, serializer):
        """Añade o actualiza la cantidad del producto en el carrito."""
        carrito = self.get_carrito()
        producto_id = self.request.data.get('producto')
        cantidad = serializer.validated_data.get('cantidad', 1)

        item_existente = ItemCarrito.objects.filter(carrito=carrito, producto_id=producto_id).first()
        
        if item_existente:
            item_existente.cantidad += cantidad
            item_existente.save()
            # Devolvemos el item actualizado con un Response manual, sobrescribiendo el comportamiento estándar de DRF
            # NOTA: Esto rompe el flujo estándar, pero es la implementación deseada.
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
        
# --- VIEWSET FALTANTE 1: Para la ruta 'items-carrito' ---
class ItemCarritoViewSet(viewsets.ModelViewSet):
    """
    CRUD directo sobre los ítems del carrito (generalmente usado por CarritoViewSet, 
    pero se define aquí para la ruta del router).
    """
    queryset = ItemCarrito.objects.all() 
    serializer_class = ItemCarritoSerializer
    permission_classes = [IsAuthenticated] 
    
    # Se recomienda fuertemente agregar lógica de filtrado aquí, similar a DireccionViewSet.
    # def get_queryset(self):
    #     # ... (asegurar que solo ve sus propios items de carrito) ...
    #     pass


class ProductosStockBajoList(generics.ListAPIView):
    """
    Retorna una lista de productos cuyo stock físico actual es <= stock mínimo.
    """
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        """Filtra los productos donde el stock_fisico es <= stock_minimo_global."""
        return Producto.objects.filter(stock_fisico__lte=F('stock_minimo_global'))

class VentaViewSet(viewsets.ModelViewSet):
    """
    CRUD para ver y gestionar ventas (solo para empleados). 
    La creación se delega a VentaCreateAPIView o al método create personalizado.
    """
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated]
    
    # Sobreescribimos el create estándar para delegar al servicio
    def create(self, request, *args, **kwargs):
        
        # 1. Utiliza un Serializer de entrada (input) para validar los datos
        serializer = VentaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # 2. Prepara los datos para el servicio
        items_data = data.pop('items')
        pagos_info = data.pop('pagos')
        
        try:
            cliente_obj = Cliente.objects.get(id=data.get('cliente_id')) if data.get('cliente_id') else None
            direccion_obj = Direccion.objects.get(id=data.get('direccion_id')) if data.get('direccion_id') else None
            
            # 3. Llama al servicio de negocio FIFO
            venta_creada = procesar_venta(
                cliente=cliente_obj,
                direccion=direccion_obj,
                items_data=items_data,
                metodo_pago_info=pagos_info,
                usuario=request.user, 
                canal=data.get('canal', 'pos'),
            )
            
            # 4. Devuelve la respuesta serializada
            respuesta_serializer = VentaSerializer(venta_creada)
            return Response(respuesta_serializer.data, status=status.HTTP_201_CREATED)
            
        except Cliente.DoesNotExist:
            return Response({'error': 'Cliente no encontrado.'}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Error interno al procesar la venta: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- VIEWSET FALTANTE 2: Para la ruta 'detalles-venta' ---
class DetalleVentaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Vista de solo lectura para los detalles de las ventas (histórico).
    """
    queryset = DetalleVenta.objects.all() 
    serializer_class = DetalleVentaSerializer
    permission_classes = [IsAuthenticated]

class PagoViewSet(viewsets.ModelViewSet):
    """
    CRUD de los pagos registrados.
    """
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    
class VentaCreateAPIView(APIView):
    """
    Endpoint dedicado para procesar una venta completa (otra opción para POS/Web).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # La lógica es idéntica al método create de VentaViewSet para mantener DRY (Don't Repeat Yourself), 
        # pero mantenemos la clase APIView si se usa en una URL específica y fuera del Router.
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
            return Response({'error': 'Error interno al procesar la venta: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================
# 3. VISTAS TRADICIONALES (Django View)
# ==========================================

def finalizar_compra_view(request):
    """
    Vista tradicional para E-commerce (NO DRF/API). Procesa la compra.
    """
    if request.method == 'POST':
        try:
            # 1. Obtener carrito por sesión
            carrito = Carrito.objects.get(session_key=request.session.session_key)
            
            items = []
            total_carrito = 0
            for item in carrito.items.all():
                items.append({'producto_id': item.producto.id, 'cantidad': item.cantidad})
                total_carrito += item.subtotal() # Asume que ItemCarrito tiene subtotal()
            
            # 2. Datos del formulario de pago
            pagos_info = {
                'metodo': request.POST.get('metodo_pago'), 
                'monto': total_carrito, # Monto total del carrito
                'referencia': request.POST.get('referencia_pago', 'N/A') 
            }
            
            # 3. Llamar al servicio
            venta_creada = procesar_venta(
                cliente=carrito.cliente,
                items_data=items,
                metodo_pago_info=pagos_info,
                usuario=request.user if request.user.is_authenticated else None,
                canal='web'
            )
            
            # 4. Limpiar carrito
            carrito.delete()
            
            return JsonResponse({'status': 'ok', 'venta_id': venta_creada.id})

        except Carrito.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'Carrito vacío o sesión expirada'}, status=400)
        except ValidationError as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
        except Exception as e:
            print(f"Error crítico en la vista: {e}")
            return JsonResponse({'status': 'error', 'mensaje': 'Error interno de procesamiento.'}, status=500)