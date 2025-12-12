from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('configuracion/', views.configuracion, name='configuracion'),
]
