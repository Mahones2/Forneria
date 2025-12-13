from django.urls import path
from . import views

urlpatterns = [
    path('resumen-financiero/', views.resumen_financiero, name='resumen-financiero'),
]
