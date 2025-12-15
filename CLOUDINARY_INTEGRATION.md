# Integración de Cloudinary para Imágenes de Productos

## 📋 Resumen
Este proyecto ahora usa **Cloudinary** para almacenar imágenes de productos en lugar de archivos locales, permitiendo que funcionen correctamente en producción (Vercel + Render).

## 🔧 Configuración Backend (Django)

### 1. Variables de Entorno en Render

Agregar estas variables en el dashboard de Render:

```bash
CLOUDINARY_CLOUD_NAME=tu_cloud_name
CLOUDINARY_API_KEY=tu_api_key
CLOUDINARY_API_SECRET=tu_api_secret
```

> **Obtener credenciales:** https://cloudinary.com/console

### 2. Modelo Producto

El campo `imagen_referencial` (ImageField) fue reemplazado por `imagen_url` (URLField):

```python
class Producto(models.Model):
    # ... otros campos ...
    imagen_url = models.URLField(max_length=500, null=True, blank=True)
```

### 3. ProductoSerializer

El serializer maneja automáticamente la subida a Cloudinary:

**Campos:**
- `imagen` (write_only): Recibe el archivo desde el frontend
- `imagen_url` (read_only): URL de Cloudinary para mostrar

**Funcionalidad:**
- En `create()`: Sube imagen a Cloudinary y guarda la URL
- En `update()`: Actualiza la imagen solo si se envía una nueva
- Optimización automática: 800x800px, quality auto

---

## 🎨 Frontend (React)

### Ejemplo: Crear Producto con Imagen

```javascript
import { useState } from 'react';
import axios from 'axios';

function CrearProducto() {
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    precio_venta: '',
    categoria: '',
    imagen: null,
    etiquetas: []
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleImageChange = (e) => {
    setFormData(prev => ({ ...prev, imagen: e.target.files[0] }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Crear FormData para enviar multipart/form-data
    const data = new FormData();
    data.append('nombre', formData.nombre);
    data.append('descripcion', formData.descripcion);
    data.append('precio_venta', formData.precio_venta);
    data.append('categoria', formData.categoria);
    
    // Agregar imagen si existe
    if (formData.imagen) {
      data.append('imagen', formData.imagen);
    }
    
    // Agregar etiquetas (array de IDs)
    formData.etiquetas.forEach(id => {
      data.append('etiquetas', id);
    });

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
      
      console.log('Producto creado:', response.data);
      // response.data.imagen_url contiene la URL de Cloudinary
      
    } catch (error) {
      console.error('Error:', error.response?.data);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        name="nombre"
        placeholder="Nombre del producto"
        value={formData.nombre}
        onChange={handleInputChange}
        required
      />
      
      <textarea
        name="descripcion"
        placeholder="Descripción"
        value={formData.descripcion}
        onChange={handleInputChange}
      />
      
      <input
        type="number"
        name="precio_venta"
        placeholder="Precio"
        value={formData.precio_venta}
        onChange={handleInputChange}
        required
      />
      
      <select
        name="categoria"
        value={formData.categoria}
        onChange={handleInputChange}
        required
      >
        <option value="">Seleccionar categoría</option>
        <option value="1">Panadería</option>
        <option value="2">Pastelería</option>
      </select>
      
      <input
        type="file"
        accept="image/*"
        onChange={handleImageChange}
      />
      
      <button type="submit">Crear Producto</button>
    </form>
  );
}

export default CrearProducto;
```

### Ejemplo: Editar Producto (PATCH)

```javascript
const actualizarProducto = async (productoId) => {
  const data = new FormData();
  
  // Solo agregar campos que cambian
  data.append('nombre', 'Nombre Actualizado');
  
  // Cambiar imagen (opcional)
  if (nuevaImagen) {
    data.append('imagen', nuevaImagen);
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
    
    console.log('Imagen actualizada:', response.data.imagen_url);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

### Ejemplo: Mostrar Imagen

```javascript
function ProductoCard({ producto }) {
  return (
    <div className="producto-card">
      <h3>{producto.nombre}</h3>
      
      {producto.imagen_url ? (
        <img 
          src={producto.imagen_url} 
          alt={producto.nombre}
          style={{ width: '200px', height: '200px', objectFit: 'cover' }}
        />
      ) : (
        <div className="sin-imagen">Sin imagen</div>
      )}
      
      <p>Precio: ${producto.precio_venta}</p>
    </div>
  );
}
```

---

## 🚀 Migración de Base de Datos

### Crear migración para cambiar el campo:

```bash
python manage.py makemigrations
python manage.py migrate
```

La migración generada automáticamente:

```python
# pos/migrations/0011_auto_XXXXXX.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('pos', '0010_venta_fecha_entrega'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='producto',
            name='imagen_referencial',
        ),
        migrations.AddField(
            model_name='producto',
            name='imagen_url',
            field=models.URLField(blank=True, help_text='URL de la imagen en Cloudinary', max_length=500, null=True),
        ),
    ]
```

---

## 🔒 Buenas Prácticas de Seguridad

### 1. CORS (Ya configurado en settings.py)

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://forneria-frontend.vercel.app",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['authorization', 'content-type', 'x-csrftoken']
```

### 2. Validación de Archivos

Agregar en el serializer (opcional):

```python
def validate_imagen(self, value):
    """Validar tamaño y tipo de archivo"""
    if value:
        # Máximo 5MB
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("La imagen no debe superar 5MB")
        
        # Tipos permitidos
        if not value.content_type.startswith('image/'):
            raise serializers.ValidationError("El archivo debe ser una imagen")
    
    return value
```

### 3. Autenticación

El endpoint requiere autenticación JWT:

```javascript
headers: {
  'Authorization': `Bearer ${accessToken}`
}
```

### 4. Rate Limiting (Recomendado)

Agregar en `settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

---

## 📊 Optimizaciones de Rendimiento

### 1. Transformaciones de Cloudinary

El backend aplica automáticamente:
- **Redimensionamiento:** Máximo 800x800px
- **Compresión:** `quality: auto:good`
- **Formato:** Auto-optimizado por Cloudinary

### 2. Lazy Loading en Frontend

```javascript
<img 
  src={producto.imagen_url} 
  loading="lazy"
  alt={producto.nombre}
/>
```

### 3. Placeholder mientras carga

```javascript
const [imageLoaded, setImageLoaded] = useState(false);

<div className="image-container">
  {!imageLoaded && <Spinner />}
  <img 
    src={producto.imagen_url}
    onLoad={() => setImageLoaded(true)}
    style={{ display: imageLoaded ? 'block' : 'none' }}
  />
</div>
```

---

## 🧪 Testing

### Test de subida en desarrollo:

```bash
curl -X POST http://localhost:8000/pos/api/productos/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "nombre=Test Producto" \
  -F "precio_venta=1000" \
  -F "categoria=1" \
  -F "imagen=@/path/to/image.jpg"
```

---

## 🐛 Troubleshooting

### Problema: "No se sube la imagen"

**Solución:**
1. Verificar variables de entorno en Render
2. Revisar logs del backend: `heroku logs --tail` o Render dashboard
3. Confirmar que el frontend envía `Content-Type: multipart/form-data`

### Problema: "CORS error"

**Solución:**
1. Verificar que el frontend está en `CORS_ALLOWED_ORIGINS`
2. No usar `Content-Type: application/json` con FormData
3. Incluir credenciales: `axios.defaults.withCredentials = true`

### Problema: "Imagen no se muestra"

**Solución:**
1. Verificar que `imagen_url` no es null en la respuesta
2. Comprobar HTTPS en producción
3. Revisar CSP headers si los usas

---

## 📝 Checklist de Despliegue

- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Configurar variables de entorno en Render
- [ ] Ejecutar migraciones: `python manage.py migrate`
- [ ] Hacer push al repo
- [ ] Verificar que Render redespliega automáticamente
- [ ] Probar endpoint de creación desde Postman/frontend
- [ ] Confirmar que la URL de Cloudinary se guarda correctamente

---

## 🎯 Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/pos/api/productos/` | Listar productos |
| POST | `/pos/api/productos/` | Crear producto con imagen |
| GET | `/pos/api/productos/{id}/` | Detalle de producto |
| PUT/PATCH | `/pos/api/productos/{id}/` | Actualizar producto/imagen |
| DELETE | `/pos/api/productos/{id}/` | Eliminar producto |

---

## 📚 Recursos

- [Cloudinary Docs](https://cloudinary.com/documentation)
- [Django Cloudinary Storage](https://github.com/klis87/django-cloudinary-storage)
- [DRF File Upload](https://www.django-rest-framework.org/api-guide/parsers/#fileuploadparser)
