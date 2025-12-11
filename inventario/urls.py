from django.urls import path
from . import views

urlpatterns = [
    path("", views.inventario_list, name="inventario_list"),
    path("dashboard/", views.dashboard_inventario, name="dashboard_inventario"),
]
