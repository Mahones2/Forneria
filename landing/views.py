from django.shortcuts import render, redirect

# Create your views here.

def home(request):
    """
    Página raíz: redirige al módulo POS.
    """
    return redirect('/pos/')

def configuracion(request):
    """
    Redirecciona al panel de administración de Django
    """
    return redirect('/admin/')
