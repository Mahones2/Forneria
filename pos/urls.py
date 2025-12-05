from django.urls import path,include
from django.contrib.auth.decorators import login_required
from rest_framework.routers import DefaultRouter
from dj_rest_auth.views import LoginView, LogoutView
from . import views

router = DefaultRouter()

# Catálogo e Inventario
router.register(r'categorias', views.CategoriaViewSet)
router.register(r'nutricionales', views.NutricionalViewSet)
router.register(r'lotes', views.LoteViewSet)
router.register(r'productos', views.ProductoViewSet)
router.register(r'alertas', views.AlertaViewSet)

# Actores y Logística
router.register(r'clientes', views.ClienteViewSet)
router.register(r'direcciones', views.DireccionViewSet) # para gestionar direcciones del cliente
router.register(r'empleados', views.EmpleadoViewSet)
router.register(r'turnos', views.TurnoViewSet)

# E-commerce y Ventas
router.register(r'carrito', views.CarritoViewSet) # para la gestión del carrito
router.register(r'ventas', views.VentaViewSet)
router.register(r'pagos', views.PagoViewSet)
router.register(r'detalle-ventas', views.DetalleVentaViewSet)

# Trazabilidad
router.register(r'movimientos-inventario', views.MovimientoInventarioViewSet)

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path("sistema/", login_required(views.inicio), name='inicio'),
    path("dashboard/", login_required(views.dashboard), name='dashboard'),
    # Páginas internas navegables desde la barra lateral (UI)
    path("ventas/", login_required(views.ventas_page), name='ventas'),
    path("inventario/", login_required(views.inventario_page), name='inventario'),
    path("inventario/producto/create/", login_required(views.producto_create), name='producto_create'),
    path("inventario/producto/<int:pk>/edit/", login_required(views.producto_edit), name='producto_edit'),
    path("inventario/producto/<int:pk>/delete/", login_required(views.producto_delete), name='producto_delete'),
    # Lotes
    path("inventario/producto/<int:product_id>/lotes/", login_required(views.product_lotes), name='product_lotes'),
    path("inventario/producto/<int:product_id>/lotes/create/", login_required(views.lote_create), name='lote_create_product'),
    path("inventario/lote/<int:pk>/edit/", login_required(views.lote_edit), name='lote_edit'),
    path("inventario/lote/<int:pk>/delete/", login_required(views.lote_delete), name='lote_delete'),
    # Server time endpoint used by POS frontend to display server timestamp in modal
    # path("server-time/", views.server_time, name='server_time'),  # COMENTADO: view no existe
    path("pedidos/", login_required(views.pedidos_page), name='pedidos'),
    path("clientes/", login_required(views.clientes_page), name='clientes'),
    path("clientes/<str:rut>/", login_required(views.cliente_detail), name='cliente_detail'),
    path("reportes/", login_required(views.reportes_page), name='reportes'),
    # API REST (router) al final para no colisionar con las páginas UI
    path('', include(router.urls)),

    # Rutas de autenticación (dj-rest-auth)
    path('auth/login/', LoginView.as_view(), name='rest_login'),
    path('auth/logout/', LogoutView.as_view(), name='rest_logout'),

    # path('vender/', views.VentaCreateAPIView.as_view(), name='venta-crear-segura'),  # COMENTADO: view no existe

    # Rutas para reportes
    path('reportes/stock-bajo/', views.ProductosStockBajoList.as_view(), name='reporte-stock-bajo'),
]
