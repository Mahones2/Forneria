# Analytics App - Dashboard de Métricas Financieras

## Descripción

App Django para análisis de métricas financieras y de inventario del sistema POS Forneria.

## Endpoints Disponibles

### 📊 Finanzas - Resumen General

#### `GET /analytics/finanzas/resumen/`
Resumen general de ventas en un periodo.

**Query Parameters:**
- `fecha_inicio` (opcional): YYYY-MM-DD (default: hace 30 días)
- `fecha_fin` (opcional): YYYY-MM-DD (default: hoy)

**Response:**
```json
{
  "total_ventas": 1250000.50,
  "cantidad_transacciones": 145,
  "ticket_promedio": 8620.69,
  "total_sin_iva": 1050420.17,
  "total_iva": 199580.33,
  "total_descuentos": 45000.00,
  "fecha_inicio": "2025-10-25",
  "fecha_fin": "2025-11-24"
}
```

---

#### `GET /analytics/finanzas/kpis-hoy/`
KPIs del día actual para cards del dashboard.

**Response:**
```json
{
  "hoy": {
    "total": 125000.00,
    "cantidad": 23
  },
  "ayer": {
    "total": 98000.00,
    "cantidad": 18
  },
  "variacion_pct": 27.55
}
```

---

### 📈 Finanzas - Gráficos Temporales

#### `GET /analytics/finanzas/ventas-diarias/`
Ventas agrupadas por día (formato Chart.js).

**Query Parameters:**
- `fecha_inicio` (opcional): YYYY-MM-DD
- `fecha_fin` (opcional): YYYY-MM-DD

**Response:**
```json
{
  "labels": ["2025-11-01", "2025-11-02", "..."],
  "totales": [45000.50, 52000.00, "..."],
  "cantidades": [12, 15, "..."]
}
```

---

#### `GET /analytics/finanzas/ventas-por-hora/`
Distribución de ventas por hora del día (últimos 7 días).

**Response:**
```json
{
  "labels": ["00:00", "01:00", "...", "23:00"],
  "totales": [0, 0, 5000, "..."],
  "cantidades": [0, 0, 3, "..."]
}
```

---

#### `GET /analytics/finanzas/comparativa-mensual/`
Comparativa de ventas de los últimos N meses.

**Query Parameters:**
- `meses` (opcional): int, default: 6

**Response:**
```json
{
  "labels": ["Junio 2025", "Julio 2025", "..."],
  "totales": [450000.00, 520000.00, "..."],
  "cantidades": [234, 267, "..."]
}
```

---

### 🛍️ Finanzas - Análisis de Productos

#### `GET /analytics/finanzas/productos-top/`
Top productos más vendidos por cantidad e ingresos.

**Query Parameters:**
- `limite` (opcional): int, default: 10
- `fecha_inicio` (opcional): YYYY-MM-DD
- `fecha_fin` (opcional): YYYY-MM-DD

**Response:**
```json
[
  {
    "producto_id": 5,
    "nombre": "Pan Integral",
    "categoria": "Panadería",
    "cantidad_vendida": 342,
    "ingresos": 855000.00,
    "transacciones": 89
  },
  "..."
]
```

---

#### `GET /analytics/finanzas/ventas-por-categoria/`
Distribución de ventas por categoría (para gráfico de dona/pie).

**Query Parameters:**
- `fecha_inicio` (opcional): YYYY-MM-DD
- `fecha_fin` (opcional): YYYY-MM-DD

**Response:**
```json
{
  "labels": ["Panadería", "Pastelería", "Bebidas"],
  "totales": [450000.00, 320000.00, 180000.00],
  "cantidades": [1200, 890, 450]
}
```

---

### 🏪 Finanzas - Otros Análisis

#### `GET /analytics/finanzas/ventas-por-canal/`
Comparativa de ventas por canal (presencial vs delivery).

**Query Parameters:**
- `fecha_inicio` (opcional): YYYY-MM-DD
- `fecha_fin` (opcional): YYYY-MM-DD

**Response:**
```json
[
  {
    "canal": "presencial",
    "total": 850000.00,
    "cantidad": 234,
    "ticket_promedio": 3632.48
  },
  {
    "canal": "delivery",
    "total": 400000.00,
    "cantidad": 89,
    "ticket_promedio": 4494.38
  }
]
```

---

#### `GET /analytics/finanzas/clientes-top/`
Top clientes por volumen de compras.

**Query Parameters:**
- `limite` (opcional): int, default: 10
- `fecha_inicio` (opcional): YYYY-MM-DD
- `fecha_fin` (opcional): YYYY-MM-DD

**Response:**
```json
[
  {
    "cliente_id": 12,
    "nombre": "Juan Pérez",
    "rut": "12345678-9",
    "total_compras": 125000.00,
    "num_compras": 23,
    "ticket_promedio": 5434.78
  },
  "..."
]
```

---

## Arquitectura

### Estructura de Archivos

```
analytics/
├── __init__.py
├── apps.py
├── admin.py
├── models.py           # Sin modelos (usamos vistas agregadas)
├── services.py         # Lógica de negocio con Django ORM
├── serializers.py      # Serialización de datos
├── views.py            # API endpoints
├── urls.py             # Routing
├── tests.py
└── README.md
```

### Stack Tecnológico

**Backend:**
- Django ORM (aggregations, annotations)
- Django REST Framework
- django-filter (para filtros avanzados)
- python-dateutil (manejo de fechas)

**Frontend (próximo paso):**
- Chart.js 4.x
- Bootstrap 5 (opcional)
- Vanilla JavaScript

---

## Instalación

1. Actualizar dependencias:
```bash
pip install -r requirements.txt
```

2. La app ya está registrada en `INSTALLED_APPS` (settings.py)

3. No requiere migraciones (no tiene modelos propios)

4. Verificar endpoints:
```bash
python manage.py runserver
# Visitar: http://127.0.0.1:8000/analytics/finanzas/resumen/
```

---

## Uso con Chart.js (Frontend)

### Ejemplo: Gráfico de Ventas Diarias

```javascript
// dashboard-finanzas.js
async function loadVentasDiarias() {
    const response = await fetch('/analytics/finanzas/ventas-diarias/?fecha_inicio=2025-11-01');
    const data = await response.json();

    const ctx = document.getElementById('chartVentas').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Ventas Diarias ($)',
                data: data.totales,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Ventas Últimos 30 Días'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString('es-CL');
                        }
                    }
                }
            }
        }
    });
}
```

---

## Próximos Pasos

1. ✅ Backend completo de métricas financieras
2. ⏳ Crear template HTML del dashboard
3. ⏳ Integrar Chart.js y visualizaciones
4. ⏳ Agregar filtros dinámicos por fecha
5. ⏳ Implementar métricas de inventario (InventarioMetrics)
6. ⏳ Dashboard de inventario con alertas
7. ⏳ Cache de métricas (Redis opcional)
8. ⏳ Export a PDF/Excel

---

## Notas Técnicas

- Todas las métricas usan Django ORM nativo (no Pandas)
- Optimizadas con `select_related`, `prefetch_related` y `annotate`
- Formato de respuesta compatible con Chart.js
- Manejo de fechas con zona horaria `America/Santiago`
- Decimales con precisión de 2 dígitos

---

## Testing

```bash
# Ejecutar tests (próximamente)
python manage.py test analytics
```

---

## Contribución

Para agregar nuevas métricas:

1. Agregar método estático en `services.py` (FinanzasMetrics o InventarioMetrics)
2. Crear serializer en `serializers.py`
3. Crear vista en `views.py`
4. Registrar URL en `urls.py`
5. Documentar en este README
