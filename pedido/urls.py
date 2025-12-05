from django.urls import path
from . import views

urlpatterns = [
    path('algo/', views.pedido, name='pedido'),
]
