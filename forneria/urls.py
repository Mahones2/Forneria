from django.contrib import admin
from django.urls import path,include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('pos/', include('pos.urls')),
    path('analytics/', include('analytics.urls')),
    path('inventario/', include('inventario.urls')),
    path('api/auth/', include('dj_rest_auth.urls')),  # login/logout con JWT

    # Esquema OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Documentación ReDoc
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

""" End points
/api/auth/login/ → login con JWT.

/api/auth/logout/ → logout.

/api/auth/token/refresh/ → refrescar token.

/api/auth/registration/ → registro de usuarios

/pos/... """