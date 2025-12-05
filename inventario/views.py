from django.shortcuts import render, get_object_or_404, redirect
from pos.models import Producto, Categoria
def inventario_list(request):
    
    categorias = Categoria.objects.all().order_by('nombre')
    
    contexto = {
        'categorias': categorias,
    }
    
    return render(request, "inventario/inventario.html", contexto)

def producto_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == "POST":
        producto.delete()
        return redirect("inventario_list") 
        
    return render(request, "inventario/producto_confirm_delete.html", {"producto": producto})
