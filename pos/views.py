# Django Core
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

# Python Standard Library
import csv
from decimal import Decimal
import requests

# Django REST Framework
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import api_view, action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Módulos Locales
from .serializers import (
    CategoriaSerializer, NutricionalSerializer, LoteSerializer, ProductoSerializer, 
    AlertaSerializer, ClienteSerializer, VentaSerializer, PagoSerializer, 
    DetalleVentaSerializer, MovimientoInventarioSerializer, EmpleadoSerializer, 
    TurnoSerializer, DireccionSerializer, ItemCarritoSerializer, CarritoSerializer
)
from .models import (
    Categoria, Nutricional, Lote, Producto, Alerta, Cliente, Venta, Pago, 
    DetalleVenta, MovimientoInventario, Empleado, Turno, Direccion, Carrito, 
    ItemCarrito
)
from .forms import ProductoForm, LoteForm
from .services import procesar_venta
from django.utils.text import slugify
from django.contrib.staticfiles import finders
# Create your views here.

@api_view(['GET'])
def server_time(request):
    """Return current server time in ISO and a human formatted string (es-CL).

    This endpoint is used by the POS frontend to show a server-based timestamp
    when confirming a sale.
    """
    now = timezone.now()
    try:
        formatted = now.astimezone(timezone.get_current_timezone()).strftime('%d/%m/%Y %H:%M')
    except Exception:
        formatted = now.strftime('%Y-%m-%d %H:%M')
    return Response({'now': now.isoformat(), 'formatted': formatted})

#API REST
class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class NutricionalViewSet(viewsets.ModelViewSet):
    queryset = Nutricional.objects.all()
    serializer_class = NutricionalSerializer

class LoteViewSet(viewsets.ModelViewSet):
    queryset = Lote.objects.all()
    serializer_class = LoteSerializer
    
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer

class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer

class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()
    serializer_class = MovimientoInventarioSerializer

class EmpleadoViewSet(viewsets.ModelViewSet):
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer

class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer
    



def finalizar_compra_view(request):
    if request.method == 'POST':
        try:
            # 1. Obtener datos del carrito del usuario
            carrito = Carrito.objects.get(session_key=request.session.session_key)
            items = []
            for item in carrito.items.all():
                items.append({'producto_id': item.producto.id, 'cantidad': item.cantidad})
            
            # 2. Datos del formulario de pago
            pago_info = {
                'metodo': request.POST.get('metodo_pago'), # 'DEB', 'CRE', etc
                'monto': 0, # Se calculará o validará adentro
                'referencia': 'TRANSBANK-123' 
            }
            
            # 3. Llamar al servicio MÁGICO
            venta_creada = procesar_venta(
                cliente=carrito.cliente,
                items_data=items,
                metodo_pago_info=pago_info,
                canal='web'
            )
            
            # 4. Limpiar carrito tras éxito
            carrito.delete()
            
            return JsonResponse({'status': 'ok', 'venta_id': venta_creada.id})

        except ValidationError as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': 'Error interno'}, status=500)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permite acceso de lectura a todos, pero solo el propietario puede editar/eliminar."""
    def has_object_permission(self, request, view, obj):
        # Permite GET, HEAD, OPTIONS (métodos seguros) a cualquiera
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permite escritura (PUT, PATCH, DELETE) solo si el usuario es el dueño
        # Asumiendo que el User de Django está asociado al Cliente
        if not hasattr(request.user, 'empleado'):
            return False # Solo empleados registrados pueden usar el sistema de cliente
            
        cliente = request.user.empleado.cliente # Asumiendo relación User -> Empleado -> Cliente
        return obj.cliente == cliente

class DireccionViewSet(viewsets.ModelViewSet):
    """
    CRUD para las direcciones de un cliente.
    """
    queryset = Direccion.objects.all() 
    serializer_class = DireccionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        """Devuelve solo las direcciones del cliente asociado al usuario logueado."""
        user = self.request.user
        
        if not hasattr(user, 'empleado'):
             raise PermissionDenied("Acceso denegado. No está asociado a un Empleado.")
        
        try:
            cliente = user.empleado.cliente
            return Direccion.objects.filter(cliente=cliente)
        except Cliente.DoesNotExist:
            raise PermissionDenied("El usuario no está asociado a un Cliente válido.")

    def perform_create(self, serializer):
        """Asigna automáticamente el cliente logueado a la nueva dirección."""
        user = self.request.user
        cliente = user.empleado.cliente
        serializer.save(cliente=cliente)


def inicio(request):
    """Vista para la página de inicio del POS con productos y categorías."""
    # Intentar obtener datos por ORM
    try:
        categorias_qs = Categoria.objects.all()
        productos_qs = Producto.objects.select_related('categoria').prefetch_related('lotes').all()

        # Filtros
        buscar = request.GET.get("buscar", "").strip()
        categoria_filtro = request.GET.get("categorias", "").strip()

        if buscar:
            productos_qs = productos_qs.filter(models.Q(nombre__icontains=buscar) | models.Q(codigo_barra__startswith=buscar))

        if categoria_filtro:
            productos_qs = productos_qs.filter(categoria__id=categoria_filtro)

        # Convertir a lista de dicts tal como la plantilla espera (campos mínimos)
        productos = []
        # lista de imágenes disponibles para asignar por rotación si no hay coincidencia exacta
        fallback_images = ['ensalada.jpg','panini.jpg','ciabata.jpg','integral.jpg','masa_madre.jpg','canela.jpg','lasagna.jpg','pasta.jpg','pescado.jpg']
        for idx, p in enumerate(productos_qs):
            productos.append({
                'id': p.id,
                'nombre': p.nombre,
                'codigo_barra': p.codigo_barra,
                'precio': float(p.precio_venta) if p.precio_venta is not None else 0,
                'stock_total': p.stock_total(),
                'categoria': p.categoria.id if p.categoria else None,
            })

        categorias = [{'id': c.id, 'nombre': c.nombre} for c in categorias_qs]

    except Exception:
        # Fallback: usar API HTTP si algo falla con la ORM (evita romper la vista)
        try:
            productos = requests.get("http://127.0.0.1:8000/pos/productos/").json()
            categorias = requests.get("http://127.0.0.1:8000/pos/categorias/").json()
        except Exception:
            productos = []
            categorias = []

    # Paginación
    paginator = Paginator(productos, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "pos.html", {
        "categorias": categorias,
        "page_obj": page_obj
    })
        
class CarritoViewSet(viewsets.ModelViewSet):
    """
    Gestión de los items dentro del Carrito de Compra (E-commerce).
    Un usuario/sesión solo puede interactuar con su propio carrito.
    """
    queryset = ItemCarrito.objects.all()
    serializer_class = ItemCarritoSerializer
    # Permitimos acceso incluso a no autenticados (usando session_key)
    permission_classes = [permissions.AllowAny] 

    def get_carrito(self):
        """Obtiene o crea el carrito activo para el usuario/sesión."""
        user = self.request.user
        
        if user.is_authenticated:
            # Opción 1: Usuario autenticado (asumiendo User -> Empleado -> Cliente)
            try:
                cliente = user.empleado.cliente
                carrito, created = Carrito.objects.get_or_create(cliente=cliente)
                # Si existe un carrito por sesión, lo migramos al cliente
                if self.request.session.session_key:
                    ses_carrito = Carrito.objects.filter(session_key=self.request.session.session_key).first()
                    if ses_carrito and ses_carrito.id != carrito.id:
                        # Migrar items del carrito temporal al carrito del cliente
                        ItemCarrito.objects.filter(carrito=ses_carrito).update(carrito=carrito)
                        ses_carrito.delete()
                return carrito
            except Exception:
                # Si no está asociado a Cliente, usa la sesión como fallback
                pass
        
        # Opción 2: Usuario anónimo (usando session_key)
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.save()
            session_key = self.request.session.session_key
            
        carrito, created = Carrito.objects.get_or_create(session_key=session_key, cliente__isnull=True)
        return carrito

    def get_queryset(self):
        """Filtra los items para mostrar solo el contenido del carrito activo."""
        carrito = self.get_carrito()
        return ItemCarrito.objects.filter(carrito=carrito).order_by('id')

    def perform_create(self, serializer):
        """Crea el ItemCarrito, asociándolo al carrito activo."""
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
        """Vacía todos los items del carrito."""
        carrito = self.get_carrito()
        carrito.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Devuelve el resumen del carrito con totales."""
        carrito = self.get_carrito()
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)


def landing(request):
    """Landing pública: mostrar categorías y productos destacados."""
    try:
        categorias_qs = Categoria.objects.all()
        # permitir filtrar por categoría via GET ?categorias=<id>
        categoria_filtro = request.GET.get('categorias', '').strip()
        productos_qs = Producto.objects.select_related('categoria').prefetch_related('lotes').all()
        if categoria_filtro:
            productos_qs = productos_qs.filter(categoria__id=categoria_filtro)
        productos_qs = productos_qs[:24]

        categorias = [{'id': c.id, 'nombre': c.nombre} for c in categorias_qs]
        productos = []
        for p in productos_qs:
            # Determinar imagen estática disponible para este producto probando varias rutas
            nombre_slug = slugify(p.nombre or '')
            candidates = [
                f"images/landing_forneria/{nombre_slug}.jpg",
                f"images/{nombre_slug}.jpg",
                f"images/landing_forneria/{p.nombre}.jpg",
                f"images/{p.nombre}.jpg",
            ]
            found = None
            for c in candidates:
                try:
                    if finders.find(c):
                        found = c
                        break
                except Exception:
                    continue
            if not found:
                # asignar por rotación una imagen del conjunto disponible
                try:
                    candidate_img = fallback_images[idx % len(fallback_images)]
                    candidate_path = f'images/landing_forneria/{candidate_img}'
                    if finders.find(candidate_path):
                        found = candidate_path
                    else:
                        found = 'images/PHOTO.jpg'
                except Exception:
                    found = 'images/PHOTO.jpg'

            productos.append({
                'id': p.id,
                'nombre': p.nombre,
                'codigo_barra': p.codigo_barra,
                'precio': float(p.precio) if p.precio is not None else None,
                'stock_total': p.stock_total(),
                # pasar id y nombre de la categoría para permitir enlaces/filtrado en la plantilla
                'categoria': {'id': p.categoria.id, 'nombre': p.categoria.nombre} if p.categoria else None,
                'imagen': found,
            })

        # Lista curada (orden y nombres) basada en las imágenes presentes en static/images/landing_forneria
        curated = [
            {'nombre': 'Bowl Ensalada', 'imagen': 'images/landing_forneria/ensalada.jpg', 'descripcion': 'Mix de hojas frescas con aderezo especial.'},
            {'nombre': 'Panini Artesanal', 'imagen': 'images/landing_forneria/panini.jpg', 'descripcion': 'Pan italiano tradicional.'},
            {'nombre': 'Ciabata', 'imagen': 'images/landing_forneria/ciabata.jpg', 'descripcion': 'Pan rústico italiano.'},
            {'nombre': 'Pan Integral', 'imagen': 'images/landing_forneria/integral.jpg', 'descripcion': 'Rico en fibra, elaborado con granos enteros y semillas.'},
            {'nombre': 'Pan de Masa Madre', 'imagen': 'images/landing_forneria/masa_madre.jpg', 'descripcion': 'Fermentación natural de 24 horas para un sabor único.'},
            {'nombre': 'Rollos de Canela', 'imagen': 'images/landing_forneria/canela.jpg', 'descripcion': 'Pan dulce glaseado con azúcar de canela.'},
            {'nombre': 'Lasagnas Caseras', 'imagen': 'images/landing_forneria/lasagna.jpg', 'descripcion': ''},
            {'nombre': 'Pastas italianas', 'imagen': 'images/landing_forneria/pasta.jpg', 'descripcion': ''},
            {'nombre': 'Pescados y Mariscos', 'imagen': 'images/landing_forneria/pescado.jpg', 'descripcion': ''},
        ]

        # Si la BD no contiene productos de la forneria (o no coincide con la curación), usamos la lista curada
        names_in_db = {p['nombre'].lower() for p in productos}
        curated_names = {c['nombre'].lower() for c in curated}
        # si no hay intersección suficiente, sustituimos
        if len(products_intersection := (names_in_db & curated_names)) < 3:
            productos = []
            for c in curated:
                productos.append({
                    'id': None,
                    'nombre': c['nombre'],
                    'codigo_barra': None,
                    'precio': None,
                    'stock_total': 0,
                    'categoria': None,
                    'imagen': c['imagen'],
                    'descripcion': c.get('descripcion',''),
                })
    except Exception:
        # fallback seguro
        categorias = []
        productos = []

    return render(request, 'landing.html', {'categorias': categorias, 'productos': productos, 'categoria_selected': categoria_filtro})


def dashboard(request):
    """Dashboard simple: totales por día y por mes para los últimos 60 días."""
    # Totales por día (últimos 60 días)
    from django.utils import timezone
    from django.db.models import Value, CharField
    from django.db.models.functions import Concat, ExtractYear, ExtractMonth, ExtractDay, Substr
    
    hoy = timezone.now()
    fecha_inicio = hoy - timezone.timedelta(days=60)

    ventas_qs = Venta.objects.filter(fecha__gte=fecha_inicio)

    # Usar DATE() de SQL directamente para MySQL
    por_dia = (
        ventas_qs
        .extra(select={'dia': 'DATE(fecha)'})
        .values('dia')
        .annotate(total=Sum('total'))
        .order_by('dia')
    )

    por_mes = (
        Venta.objects
        .extra(select={'mes': 'DATE_FORMAT(fecha, "%%Y-%%m-01")'})
        .values('mes')
        .annotate(total=Sum('total'))
        .order_by('mes')
    )

    # Convertir QuerySets a listas serializables
    dias = [ { 'dia': str(r['dia']) if r['dia'] else '', 'total': float(r['total'] or 0) } for r in por_dia ]
    meses = [ { 'mes': str(r['mes']) if r['mes'] else '', 'total': float(r['total'] or 0) } for r in por_mes ]

    # KPIs simples (últimos 30 días + hoy)
    fecha_30 = hoy - timezone.timedelta(days=30)
    ventas_30_qs = Venta.objects.filter(fecha__gte=fecha_30)

    total_ingresos_30 = ventas_30_qs.aggregate(s=Sum('total'))['s'] or 0
    total_ventas_30 = ventas_30_qs.aggregate(c=Count('id'))['c'] or 0
    promedio_venta_30 = ventas_30_qs.aggregate(a=Avg('total'))['a'] or 0

    ventas_hoy = Venta.objects.filter(fecha__date=hoy.date()).aggregate(c=Count('id'))['c'] or 0

    kpis = {
        'total_ingresos_30': float(total_ingresos_30),
        'total_ventas_30': int(total_ventas_30),
        'promedio_venta_30': float(promedio_venta_30),
        'ventas_hoy': int(ventas_hoy),
    }

    return render(request, 'pos_dashboard.html', { 'dias': dias, 'meses': meses, 'kpis': kpis })


def ventas_page(request):
    """Página pública interna que lista las ventas recientes."""
    # soportar filtros por cliente (rut o nombre) vía GET
    rut = request.GET.get('rut', '').strip()
    nombre = request.GET.get('nombre', '').strip()

    qs = Venta.objects.select_related('cliente', 'empleado').order_by('-fecha')

    if rut:
        qs = qs.filter(cliente__rut__iexact=rut)
    if nombre:
        qs = qs.filter(cliente__nombre__icontains=nombre)

    # Paginación
    page_number = request.GET.get('page', 1)
    paginator = Paginator(qs, 25)  # 25 ventas por página
    page_obj = paginator.get_page(page_number)

    return render(request, 'pos_ventas.html', {'ventas': page_obj.object_list, 'page_obj': page_obj, 'filter_rut': rut, 'filter_nombre': nombre})


def inventario_page(request):
    """Lista simple de productos e información de stock."""
    productos = Producto.objects.select_related('categoria').all()
    # La plantilla de inventario ahora vive en la app `inventario` (inventario/templates/inventario/pos_inventario.html)
    return render(request, 'inventario/pos_inventario.html', {'productos': productos})


def producto_create(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            prod = form.save()
            return render(request, 'inventario/pos_producto_form.html', {'form': form, 'saved': True, 'producto': prod})
    else:
        form = ProductoForm()
    return render(request, 'inventario/pos_producto_form.html', {'form': form})


def producto_edit(request, pk):
    prod = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=prod)
        if form.is_valid():
            prod = form.save()
            return render(request, 'inventario/pos_producto_form.html', {'form': form, 'saved': True, 'producto': prod})
    else:
        form = ProductoForm(instance=prod)
    return render(request, 'inventario/pos_producto_form.html', {'form': form, 'producto': prod})


def producto_delete(request, pk):
    prod = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        prod.delete()
        return render(request, 'inventario/pos_producto_confirm_delete.html', {'deleted': True, 'nombre': prod.nombre})
    return render(request, 'inventario/pos_producto_confirm_delete.html', {'producto': prod})


def product_lotes(request, product_id):
    producto = get_object_or_404(Producto, pk=product_id)
    lotes = producto.lotes.all().order_by('-fecha_elaboracion')
    return render(request, 'inventario/pos_lotes_list.html', {'producto': producto, 'lotes': lotes})


def lote_create(request, product_id=None):
    initial = {}
    producto = None
    if product_id:
        producto = get_object_or_404(Producto, pk=product_id)
        initial['producto'] = producto

    if request.method == 'POST':
        form = LoteForm(request.POST)
        if form.is_valid():
            lote = form.save()
            return render(request, 'inventario/pos_lote_form.html', {'form': form, 'saved': True, 'lote': lote})
    else:
        form = LoteForm(initial=initial)
    return render(request, 'inventario/pos_lote_form.html', {'form': form, 'producto': producto})


def lote_edit(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    if request.method == 'POST':
        form = LoteForm(request.POST, instance=lote)
        if form.is_valid():
            lote = form.save()
            return render(request, 'inventario/pos_lote_form.html', {'form': form, 'saved': True, 'lote': lote})
    else:
        form = LoteForm(instance=lote)
    return render(request, 'inventario/pos_lote_form.html', {'form': form, 'lote': lote})


def lote_delete(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    if request.method == 'POST':
        nombre = str(lote)
        lote.delete()
        return render(request, 'inventario/pos_lote_confirm_delete.html', {'deleted': True, 'nombre': nombre})
    return render(request, 'inventario/pos_lote_confirm_delete.html', {'lote': lote})


def clientes_page(request):
    """Página de clientes con filtros por RUT y nombre."""
    rut = request.GET.get('rut', '').strip()
    nombre = request.GET.get('nombre', '').strip()
    
    qs = Cliente.objects.all().order_by('nombre')
    
    if rut:
        qs = qs.filter(rut__icontains=rut)
    if nombre:
        qs = qs.filter(nombre__icontains=nombre)
    
    # Paginación
    page_number = request.GET.get('page', 1)
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'pos_clientes.html', {
        'clientes': page_obj.object_list,
        'page_obj': page_obj,
        'filter_rut': rut,
        'filter_nombre': nombre
    })


def pedidos_page(request):
    # No hay modelo Pedido en este app; mostrar placeholder y link a ventas
    return render(request, 'pos_pedidos.html', {})


def reportes_page(request):
    # Reusar dashboard como punto de entrada a reportes
    return dashboard(request)


def cliente_detail(request, rut):
    """Detalle de cliente: muestra información y compras paginadas. Soporta export CSV con ?export=csv"""
    cliente = get_object_or_404(Cliente, rut=rut)

    ventas_qs = Venta.objects.filter(cliente=cliente).order_by('-fecha')

    # exportar CSV si se solicita
    if request.GET.get('export') == 'csv':
        # generar CSV de ventas básicas
        response = HttpResponse(content_type='text/csv')
        filename = f"ventas_{cliente.rut}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['folio', 'fecha', 'total', 'monto_pagado', 'vuelto', 'canal_venta'])
        for v in ventas_qs:
            writer.writerow([v.folio, v.fecha.isoformat(), str(v.total), str(v.monto_pagado or ''), str(v.vuelto or ''), v.canal_venta])
        return response

    # paginación de compras del cliente
    page_number = request.GET.get('page', 1)
    paginator = Paginator(ventas_qs, 20)
    page_obj = paginator.get_page(page_number)

    return render(request, 'pos_cliente_detail.html', {'cliente': cliente, 'ventas': page_obj.object_list, 'page_obj': page_obj})


@csrf_exempt
@api_view(['POST'])
def checkout(request):
    """Endpoint simple para procesar el checkout.

    Payload esperado (JSON):
    {
      "canal_venta": "presencial",
      "cliente_rut": "12345678-9",          # opcional
      "monto_pagado": 10000,                 # opcional (number)
      "items": [
         {"producto_id": 1, "cantidad": 2, "precio_unitario": 1200, "descuento_pct": 0},
         ...
      ]
    }

    Crea Venta y DetalleVenta dentro de una transacción atómica y consume stock
    usando Venta.actualizar_stock(). Retorna JSON con id/folio/total/vuelto.
    """
    data = request.data
    items = data.get('items') or []
    if not items:
        return Response({'detail': 'No hay items en el carrito'}, status=status.HTTP_400_BAD_REQUEST)

    canal = data.get('canal_venta', 'presencial')
    cliente_rut = data.get('cliente_rut')
    monto_pagado = data.get('monto_pagado')
    metodo_pago = data.get('metodo_pago')

    try:
        # calcular totales con Decimal
        subtotal = Decimal('0')
        descuento_total = Decimal('0')
        detalles_to_create = []
        for it in items:
            pid = it.get('producto_id')
            qty = int(it.get('cantidad', 0))
            precio = Decimal(str(it.get('precio_unitario', '0')))
            desc_pct = Decimal(str(it.get('descuento_pct') or 0))
            if qty <= 0 or precio <= 0:
                raise ValueError('Cantidad y precio deben ser mayores a 0')
            linea_total = precio * qty
            descuento_linea = (linea_total * desc_pct / Decimal('100')) if desc_pct else Decimal('0')
            subtotal += linea_total
            descuento_total += descuento_linea
            detalles_to_create.append({'producto_id': pid, 'cantidad': qty, 'precio_unitario': precio, 'descuento_pct': desc_pct})

        total_sin_iva = (subtotal - descuento_total).quantize(Decimal('0.01'))
        total_iva = (total_sin_iva * Decimal('0.19')).quantize(Decimal('0.01'))
        total_con_iva = (total_sin_iva + total_iva).quantize(Decimal('0.01'))

        monto_pagado_dec = None
        vuelto = None
        if monto_pagado is not None:
            monto_pagado_dec = Decimal(str(monto_pagado)).quantize(Decimal('0.01'))
            if monto_pagado_dec < total_con_iva:
                return Response({'detail': 'El monto pagado es menor al total'}, status=status.HTTP_400_BAD_REQUEST)
            vuelto = (monto_pagado_dec - total_con_iva).quantize(Decimal('0.01'))

        with transaction.atomic():
            venta = Venta.objects.create(
                fecha=timezone.now(),
                neto=total_sin_iva,
                iva=total_iva,
                total=total_con_iva,
                canal_venta=canal
            )

            # si viene cliente_rut, enlazar cliente
            if cliente_rut:
                from .models import Cliente
                cliente, created = Cliente.objects.get_or_create(rut=cliente_rut, defaults={'nombre': None, 'correo': None})
                venta.cliente = cliente
                venta.save(update_fields=['cliente'])

            # crear detalles
            for d in detalles_to_create:
                prod = Producto.objects.get(id=d['producto_id'])
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=prod,
                    cantidad=d['cantidad'],
                    precio_unitario=d['precio_unitario'],
                    descuento_pct=d['descuento_pct']
                )

            # recalcular y guardar totales por si hay reglas adicionales
            venta.calcular_totales_desde_detalles()

            # consumir stock (puede lanzar ValueError si no hay stock suficiente)
            venta.actualizar_stock()

            # asignar folio simple
            venta.folio = f"V{venta.id:06d}"
            venta.save(update_fields=['folio'])

            # Registrar pago asociado (si se envía método de pago)
            try:
                pago_monto = monto_pagado_dec if monto_pagado_dec is not None else total_con_iva
                if metodo_pago:
                    Pago.objects.create(venta=venta, monto=pago_monto, metodo=metodo_pago)
            except Exception:
                # No bloquear la venta si falla el registro del pago; loguear en futuro
                pass

        resp = {
            'id': venta.id,
            'folio': venta.folio,
            'total': str(venta.total),
            'vuelto': str(vuelto) if vuelto is not None else None
        }
        return Response(resp, status=status.HTTP_201_CREATED)

    except Producto.DoesNotExist:
        return Response({'detail': 'Producto no encontrado'}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as ve:
        return Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'detail': 'Error al procesar la venta', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductosStockBajoList(generics.ListAPIView):
    """
    Retorna una lista de productos cuyo stock físico actual
    es menor o igual a su stock mínimo global.
    """
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        """Filtra los productos donde el stock_fisico es <= stock_minimo_global."""
        return Producto.objects.filter(stock_fisico__lte=models.F('stock_minimo_global'))
