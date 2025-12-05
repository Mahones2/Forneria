from django import forms
from pos.models import *

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "codigo_barra", "nombre", "descripcion", "marca",
            "precio", "tipo", "presentacion", "formato", "categoria"
        ]

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion"]

class NutricionalForm(forms.ModelForm):
    class Meta:
        model = Nutricional
        fields = ["calorias", "proteinas", "grasas", "carbohidratos", "azucares", "sodio"]

class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ["numero_lote", "fecha_elaboracion", "fecha_caducidad",
                  "stock_actual", "stock_minimo", "stock_maximo"]
