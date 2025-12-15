from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from dj_rest_auth.views import LoginView, LogoutView
from rest_framework_simplejwt.views import TokenRefreshView
from .views import EmpleadoDetailView
from django.conf.urls.static import static
# FALTA IMPORTAR ESTO PARA LA DOCUMENTACIÓN:
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView 

router = DefaultRouter()

# 1. Catálogo
router.register(r'categorias', views.CategoriaViewSet)
router.register(r'productos', views.ProductoViewSet)
router.register(r'nutricional', views.NutricionalViewSet)
router.register(r'etiquetas', views.EtiquetaViewSet)

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
router.register(r'empleados', views.EmpleadoViewSet, basename='empleado') # Agregado basename por seguridad
router.register(r'turnos', views.TurnoViewSet)

# 5. Ventas
router.register(r'carritos', views.CarritoViewSet, basename='carrito')
router.register(r'items-carrito', views.ItemCarritoViewSet)
router.register(r'ventas', views.VentaViewSet)
router.register(r'detalles-venta', views.DetalleVentaViewSet)
router.register(r'pagos', views.PagoViewSet)

# 6. KIOSCO
router.register(r'kiosco', views.KioscoViewSet, basename='kiosco')

urlpatterns = [
    # CRUDs automáticos del Router
    path('api/', include(router.urls)),

    # Autenticación
    path('api/auth/login/', LoginView.as_view(), name='rest_login'),
    path('api/auth/logout/', LogoutView.as_view(), name='rest_logout'),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Empleado autenticado (perfil propio)
    path('me/', EmpleadoDetailView.as_view(), name='empleado-detail'), # Le agregué /api/ para consistencia

    # Endpoints específicos
    path('api/vender/', views.VentaCreateAPIView.as_view(), name='venta-crear-segura'),
    path('api/reportes/stock-bajo/', views.ProductosStockBajoList.as_view(), name='reporte-stock-bajo'),
    
    # OPCIONAL: Si quieres mantener el catálogo en una URL corta aparte del KioscoViewSet
    path('api/catalogo/', views.CatalogoUnificadoView.as_view(), name='catalogo-simple'),

    # Documentación (Swagger/OpenAPI)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Agregué esta línea para que puedas VER la documentación en el navegador:
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]