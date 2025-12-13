from django.contrib import admin
from django.urls import path, include
from inventario import views as inventario_views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticación con dj-rest-auth
    path('api/auth/', include('dj_rest_auth.urls')),  

    # Analytics
    path('analytics/', include('analytics.urls')),

    # Dashboard Inventario (endpoint directo)
    path('dashboard/inventario/', inventario_views.dashboard_inventario_api, name='dashboard-inventario-api'),

    # Módulos principales
    path('inventario/', include('inventario.urls')),
    path('pedidos/', include('pedido.urls')),
    path('pos/', include('pos.urls')),
    path('', include('landing.urls')),
    path('reporte/', include('reportes.urls')),
    
    # Esquema OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Documentación ReDoc
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)