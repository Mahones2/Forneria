from django.shortcuts import render
import requests
# Create your views here.
def pedido(request):
    return render(request, 'pedido/pedido.html')