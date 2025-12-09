from django import forms
from .models import Producto, Lote


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'marca', 'precio_venta', 'tipo', 'presentacion', 'categoria', 'codigo_barra']


class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ['producto', 'numero_lote', 'fecha_elaboracion', 'fecha_caducidad', 'precio_costo_unitario', 'stock_inicial', 'stock_actual']
