# Configuración de Cloudinary - Producción

## 🔧 Variables de Entorno en Render

Agregar en el Dashboard de Render:

```bash
CLOUDINARY_URL=cloudinary://976481726881764:L63vlbhmY9KduFIkXuucJyKabKU@dpgc9uwwa
```

✅ Esto es todo lo que necesitas. Django parseará automáticamente la URL.

---

## 📦 Backend (Django REST Framework)

### Modelo Producto

```python
class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=300, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    
    # ✅ Solo guardamos la URL, no el archivo
    imagen_url = models.URLField(max_length=500, null=True, blank=True)
    
    etiquetas = models.ManyToManyField(Etiqueta, blank=True, related_name='productos')
```

### ProductoSerializer

```python
class ProductoSerializer(serializers.ModelSerializer):
    # Campo para RECIBIR la imagen (write-only)
    imagen = serializers.ImageField(write_only=True, required=False, allow_null=True)
    
    # Campo para DEVOLVER la URL (read-only)
    imagen_url = serializers.URLField(read_only=True)
    
    def create(self, validated_data):
        imagen = validated_data.pop('imagen', None)
        producto = super().create(validated_data)
        
        if imagen:
            try:
                result = cloudinary.uploader.upload(
                    imagen,
                    folder=f"productos/{producto.id}",
                    public_id=f"producto_{producto.id}",
                    overwrite=True,
                    transformation=[
                        {'width': 800, 'height': 800, 'crop': 'limit'},
                        {'quality': 'auto:good'}
                    ]
                )
                producto.imagen_url = result['secure_url']
                producto.save(update_fields=['imagen_url'])
            except Exception as e:
                print(f"Error Cloudinary: {e}")
        
        return producto
    
    def update(self, instance, validated_data):
        imagen = validated_data.pop('imagen', None)
        instance = super().update(instance, validated_data)
        
        if imagen:
            try:
                result = cloudinary.uploader.upload(
                    imagen,
                    folder=f"productos/{instance.id}",
                    public_id=f"producto_{instance.id}",
                    overwrite=True,
                    transformation=[
                        {'width': 800, 'height': 800, 'crop': 'limit'},
                        {'quality': 'auto:good'}
                    ]
                )
                instance.imagen_url = result['secure_url']
                instance.save(update_fields=['imagen_url'])
            except Exception as e:
                print(f"Error Cloudinary: {e}")
        
        return instance
```

### ProductoViewSet

```python
from rest_framework import parsers

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]
    
    # ✅ Importante: Parsers para multipart/form-data
    parser_classes = [
        parsers.MultiPartParser,
        parsers.FormParser,
        parsers.JSONParser
    ]
```

---

## 🎨 Frontend (React)

### Ejemplo Completo: Crear Producto

```jsx
import { useState } from 'react';
import axios from 'axios';

function CrearProducto() {
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    precio_venta: '',
    categoria: '',
    imagen: null
  });
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({ ...prev, imagen: file }));
      
      // Preview local
      const reader = new FileReader();
      reader.onloadend = () => setPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    // ✅ Crear FormData para multipart/form-data
    const data = new FormData();
    data.append('nombre', formData.nombre);
    data.append('descripcion', formData.descripcion);
    data.append('precio_venta', formData.precio_venta);
    data.append('categoria', formData.categoria);
    
    // Solo agregar imagen si existe
    if (formData.imagen) {
      data.append('imagen', formData.imagen);
    }

    try {
      const response = await axios.post(
        'https://forneria-1o9s.onrender.com/pos/api/productos/',
        data,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      console.log('✅ Producto creado:', response.data);
      console.log('📷 Imagen URL:', response.data.imagen_url);
      
      alert('Producto creado exitosamente!');
      
      // Limpiar formulario
      setFormData({
        nombre: '',
        descripcion: '',
        precio_venta: '',
        categoria: '',
        imagen: null
      });
      setPreview(null);
      
    } catch (error) {
      console.error('❌ Error:', error.response?.data);
      alert('Error al crear producto');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h2>Crear Producto</h2>
      
      <div style={{ marginBottom: '1rem' }}>
        <label>Nombre:</label>
        <input
          type="text"
          name="nombre"
          value={formData.nombre}
          onChange={handleInputChange}
          required
          style={{ width: '100%', padding: '8px' }}
        />
      </div>
      
      <div style={{ marginBottom: '1rem' }}>
        <label>Descripción:</label>
        <textarea
          name="descripcion"
          value={formData.descripcion}
          onChange={handleInputChange}
          style={{ width: '100%', padding: '8px' }}
        />
      </div>
      
      <div style={{ marginBottom: '1rem' }}>
        <label>Precio:</label>
        <input
          type="number"
          step="0.01"
          name="precio_venta"
          value={formData.precio_venta}
          onChange={handleInputChange}
          required
          style={{ width: '100%', padding: '8px' }}
        />
      </div>
      
      <div style={{ marginBottom: '1rem' }}>
        <label>Categoría:</label>
        <select
          name="categoria"
          value={formData.categoria}
          onChange={handleInputChange}
          required
          style={{ width: '100%', padding: '8px' }}
        >
          <option value="">Seleccionar...</option>
          <option value="1">Panadería</option>
          <option value="2">Pastelería</option>
        </select>
      </div>
      
      <div style={{ marginBottom: '1rem' }}>
        <label>Imagen:</label>
        <input
          type="file"
          accept="image/*"
          onChange={handleImageChange}
          style={{ width: '100%', padding: '8px' }}
        />
        
        {preview && (
          <div style={{ marginTop: '1rem' }}>
            <img 
              src={preview} 
              alt="Preview" 
              style={{ 
                width: '200px', 
                height: '200px', 
                objectFit: 'cover',
                border: '1px solid #ccc'
              }} 
            />
          </div>
        )}
      </div>
      
      <button 
        type="submit" 
        disabled={loading}
        style={{ 
          padding: '10px 20px', 
          backgroundColor: loading ? '#ccc' : '#4CAF50',
          color: 'white',
          border: 'none',
          cursor: loading ? 'not-allowed' : 'pointer'
        }}
      >
        {loading ? 'Creando...' : 'Crear Producto'}
      </button>
    </form>
  );
}

export default CrearProducto;
```

### Ejemplo: Editar Producto

```jsx
function EditarProducto({ productoId }) {
  const [formData, setFormData] = useState({
    nombre: '',
    precio_venta: '',
    imagen: null
  });
  
  const handleUpdate = async () => {
    const data = new FormData();
    
    // Solo agregar campos que cambiaron
    if (formData.nombre) data.append('nombre', formData.nombre);
    if (formData.precio_venta) data.append('precio_venta', formData.precio_venta);
    
    // ✅ Imagen es opcional en edición
    if (formData.imagen) {
      data.append('imagen', formData.imagen);
    }

    try {
      const response = await axios.patch(
        `https://forneria-1o9s.onrender.com/pos/api/productos/${productoId}/`,
        data,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      console.log('✅ Producto actualizado:', response.data);
    } catch (error) {
      console.error('❌ Error:', error);
    }
  };

  return (
    <div>
      <input
        type="text"
        placeholder="Nuevo nombre"
        onChange={(e) => setFormData(prev => ({ ...prev, nombre: e.target.value }))}
      />
      
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setFormData(prev => ({ ...prev, imagen: e.target.files[0] }))}
      />
      
      <button onClick={handleUpdate}>Actualizar</button>
    </div>
  );
}
```

### Ejemplo: Mostrar Producto

```jsx
function ProductoCard({ producto }) {
  return (
    <div className="producto-card">
      <h3>{producto.nombre}</h3>
      
      {/* ✅ Usar imagen_url directamente */}
      {producto.imagen_url ? (
        <img 
          src={producto.imagen_url} 
          alt={producto.nombre}
          loading="lazy"
          style={{ 
            width: '200px', 
            height: '200px', 
            objectFit: 'cover' 
          }}
        />
      ) : (
        <div style={{ 
          width: '200px', 
          height: '200px', 
          backgroundColor: '#f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          Sin imagen
        </div>
      )}
      
      <p>Precio: ${producto.precio_venta}</p>
    </div>
  );
}
```

---

## 🚀 Migración de Base de Datos

```bash
# En local
python manage.py makemigrations
python manage.py migrate

# Commit y push
git add .
git commit -m "Migrar imágenes a Cloudinary"
git push
```

Render ejecutará automáticamente las migraciones en producción.

---

## ✅ Checklist de Despliegue

- [x] Configurar `CLOUDINARY_URL` en Render
- [x] Agregar `cloudinary==1.41.0` a requirements.txt
- [x] Cambiar modelo: `ImageField` → `URLField`
- [x] Actualizar serializer con `create()` y `update()`
- [x] Agregar parsers a ProductoViewSet
- [ ] Hacer migración y push
- [ ] Verificar despliegue en Render
- [ ] Probar creación de producto desde frontend

---

## 🐛 Troubleshooting

### Error: "No se sube la imagen"

1. Verificar `CLOUDINARY_URL` en Render
2. Ver logs: Render Dashboard → Logs
3. Confirmar que frontend envía `multipart/form-data`

### Error: CORS

Ya está configurado en `settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "https://forneria-frontend.vercel.app",
]
```

### Imagen no se muestra

Verificar que `imagen_url` no sea `null` en la respuesta:

```javascript
console.log(response.data.imagen_url);
// Debe mostrar: https://res.cloudinary.com/dpgc9uwwa/image/upload/...
```

---

## 📊 Formato de Respuesta

### POST /pos/api/productos/

```json
{
  "id": 1,
  "nombre": "Pan Francés",
  "descripcion": "Pan recién horneado",
  "precio_venta": "1500.00",
  "categoria": 1,
  "imagen_url": "https://res.cloudinary.com/dpgc9uwwa/image/upload/v1234567890/productos/1/producto_1.jpg",
  "etiquetas": []
}
```

### PATCH /pos/api/productos/1/

Si NO envías imagen:
```json
{
  "id": 1,
  "nombre": "Pan Francés Actualizado",
  "imagen_url": "https://res.cloudinary.com/dpgc9uwwa/image/upload/v1234567890/productos/1/producto_1.jpg"
}
```

Si SÍ envías imagen:
```json
{
  "id": 1,
  "nombre": "Pan Francés Actualizado",
  "imagen_url": "https://res.cloudinary.com/dpgc9uwwa/image/upload/v9999999999/productos/1/producto_1.jpg"
}
```

---

## 🎯 Endpoints

| Método | URL | Auth | Body |
|--------|-----|------|------|
| GET | `/pos/api/productos/` | No* | - |
| POST | `/pos/api/productos/` | Sí | FormData |
| GET | `/pos/api/productos/{id}/` | No* | - |
| PATCH | `/pos/api/productos/{id}/` | Sí | FormData |
| DELETE | `/pos/api/productos/{id}/` | Sí | - |

*Actualmente configurado con `AllowAny` para el catálogo público.

---

## 📚 Recursos

- [Cloudinary Docs](https://cloudinary.com/documentation/django_integration)
- [DRF Parsers](https://www.django-rest-framework.org/api-guide/parsers/)
- [FormData MDN](https://developer.mozilla.org/en-US/docs/Web/API/FormData)
