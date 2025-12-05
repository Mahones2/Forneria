"""
URLs para Inventario
"""
from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    # Dashboard HTML
    path('dashboard/', views.dashboard_inventario, name='dashboard-inventario'),
]
