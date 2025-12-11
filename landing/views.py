from django.shortcuts import render, redirect

# Create your views here.

def configuracion(request):
    """
    Redirecciona al panel de administración de Django
    """
    return redirect('/admin/')
