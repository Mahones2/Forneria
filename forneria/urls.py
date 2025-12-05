from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from pos import views as pos_views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
)

urlpatterns = [
    # Raíz -> landing pública
    path('', pos_views.landing, name='landing'),
    # Login / Logout (plantillas simples)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('dj_rest_auth.urls')),  # login/logout con JWT
    path('analytics/', include('analytics.urls')),
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