# Archivo: pedido/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PedidoViewSet

# Crear el router
router = DefaultRouter()

router.register(r'', PedidoViewSet, basename='pedido') 

urlpatterns = [
    # Incluye todas las rutas generadas por el router (GET, POST, PUT, DELETE)
    path('', include(router.urls)),
]