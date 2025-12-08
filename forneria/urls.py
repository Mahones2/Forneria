from django.contrib import admin
from django.urls import path,include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('dj_rest_auth.urls')),  
    path('inventario/', include('inventario.urls')),
    path('pedidos/', include('pedido.urls')),
    path('pos/', include('pos.urls')),
    path('',include('landing.urls')),
    path('reporte/', include('reportes.urls')),
    
    # Esquema OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Documentación ReDoc, esta wea no sirve mucho que digamos, hasta lo deprecaron asi que se puede sacar
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

""" End points
/api/auth/login/ → login con JWT.

/api/auth/logout/ → logout.

/api/auth/token/refresh/ → refrescar token.

/api/auth/registration/ → registro de usuarios

/pos/... """