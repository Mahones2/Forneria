from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from dj_rest_auth.views import LoginView, LogoutView
from rest_framework_simplejwt.views import TokenRefreshView
from .views import EmpleadoDetailView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

router = DefaultRouter()

# 1. Catálogo
router.register(r'categorias', views.CategoriaViewSet)
router.register(r'productos', views.ProductoViewSet)
router.register(r'nutricional', views.NutricionalViewSet)

# 2. Inventario y Lotes
router.register(r'ubicaciones', views.UbicacionViewSet)
router.register(r'lotes', views.LoteViewSet)
router.register(r'movimientos', views.MovimientoInventarioViewSet)
router.register(r'alertas', views.AlertaViewSet)

# 3. Abastecimiento
router.register(r'proveedores', views.ProveedorViewSet)
router.register(r'insumos', views.InsumoViewSet)
router.register(r'ordenes-compra', views.OrdenCompraViewSet)
router.register(r'ordenes-compra-items', views.OrdenCompraItemViewSet)

# 4. Actores
router.register(r'clientes', views.ClienteViewSet)
router.register(r'direcciones', views.DireccionViewSet, basename='direccion')
router.register(r'empleados', views.EmpleadoViewSet)
router.register(r'turnos', views.TurnoViewSet)

# 5. Ventas
router.register(r'carritos', views.CarritoViewSet, basename='carrito')
router.register(r'items-carrito', views.ItemCarritoViewSet)
router.register(r'ventas', views.VentaViewSet)
router.register(r'detalles-venta', views.DetalleVentaViewSet)
router.register(r'pagos', views.PagoViewSet)

urlpatterns = [
    # CRUDs
    path('api/', include(router.urls)),

    
    
    # Autenticación
    path('api/auth/login/', LoginView.as_view(), name='rest_login'),
    path('api/auth/logout/', LogoutView.as_view(), name='rest_logout'),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Empleado autenticado
    path('me/', EmpleadoDetailView.as_view(), name='empleado-detail'),

    # Ventas y reportes
    path('api/vender/', views.VentaCreateAPIView.as_view(), name='venta-crear-segura'),
    path('api/reportes/stock-bajo/', views.ProductosStockBajoList.as_view(), name='reporte-stock-bajo'),


    # Documentacion, aqui ven toda la informacion sobre las api disponibles, es automatico
    # Endpoint que devuelve el esquema OpenAPI en formato JSON
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Interfaz Swagger UI
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Interfaz Redoc
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
