# Guía de Pruebas - Backend (Django)

## 📋 Tabla de Contenidos
- [Configuración](#configuración)
- [Ejecutar Pruebas](#ejecutar-pruebas)
- [Estructura de Pruebas](#estructura-de-pruebas)
- [Cobertura de Pruebas](#cobertura-de-pruebas)

## ⚙️ Configuración

Las pruebas están configuradas en el directorio `pos/tests/`:

```
pos/tests/
├── __init__.py
├── test_validators.py    # Pruebas para validators.py
├── test_serializers.py   # Pruebas para serializers.py
└── test_models.py        # Pruebas para modelos con clean()
```

## 🚀 Ejecutar Pruebas

### Ejecutar todas las pruebas:
```bash
cd C:\Users\saemm\OneDrive\Documentos\GitHub\Forneria2
python manage.py test pos.tests
```

### Ejecutar un archivo específico de pruebas:
```bash
# Solo pruebas de validators
python manage.py test pos.tests.test_validators

# Solo pruebas de serializers
python manage.py test pos.tests.test_serializers

# Solo pruebas de modelos
python manage.py test pos.tests.test_models
```

### Ejecutar una clase de pruebas específica:
```bash
python manage.py test pos.tests.test_validators.ValidateRutFormatTest
```

### Ejecutar una prueba individual:
```bash
python manage.py test pos.tests.test_validators.ValidateRutFormatTest.test_rut_valido_con_puntos_y_guion
```

### Ejecutar con verbosidad:
```bash
python manage.py test pos.tests -v 2
```

### Ejecutar con cobertura (instalar coverage primero):
```bash
pip install coverage
coverage run --source='pos' manage.py test pos.tests
coverage report
coverage html  # Genera reporte HTML en htmlcov/
```

## 📊 Estructura de Pruebas

### test_validators.py (15+ validadores)

#### ✅ ValidateRutFormatTest
- `test_rut_valido_con_puntos_y_guion` - Formato: 12.345.678-9
- `test_rut_valido_sin_puntos_con_guion` - Formato: 12345678-9
- `test_rut_valido_con_k_mayuscula` - Dígito verificador K
- `test_rut_valido_con_k_minuscula` - Dígito verificador k
- `test_rut_invalido_sin_guion` - Debe fallar
- `test_rut_invalido_formato_incorrecto` - Debe fallar

#### ✅ ValidateUsernameTest
- `test_username_valido` - Usuario válido
- `test_username_minimo_3_caracteres` - Mínimo 3 chars
- `test_username_sin_espacios` - No permite espacios
- `test_username_solo_alfanumerico` - Solo a-z, 0-9, _
- `test_username_unique_sin_duplicados` - Unicidad

#### ✅ ValidatePasswordStrengthTest
- `test_password_valido_6_caracteres` - Mínimo 6 chars
- `test_password_corto_invalido` - Debe fallar
- `test_password_vacio_invalido` - Debe fallar

#### ✅ ValidateStockRangeTest
- `test_stock_valido_en_rango` - 0 a 9999
- `test_stock_negativo_invalido` - Debe fallar
- `test_stock_mayor_9999_invalido` - Debe fallar

#### ✅ ValidateDateTest
- `test_fecha_futura_valida` - Fecha > hoy
- `test_fecha_hoy_invalida` - Hoy debe fallar
- `test_fecha_posterior_valida` - Cross-field validation

### test_serializers.py (Validaciones DRF)

#### ✅ PagoInputSerializerTest
- Validación de pago en efectivo con monto_recibido
- Validación de monto positivo
- Cross-field: monto_recibido >= monto para efectivo

#### ✅ VentaInputSerializerTest
- Validación de venta con items y pagos
- Debe tener al menos 1 item
- Debe tener al menos 1 pago

#### ✅ ClienteSerializerTest
- Validación formato RUT chileno
- Validación email único
- Validación teléfono chileno

#### ✅ EmpleadoSerializerTest
- Validación username sin espacios
- Validación unicidad username
- Validación password >= 6 caracteres

#### ✅ ProductoSerializerTest
- Validación precio_venta > 0
- Validación stock_minimo >= 0
- Validación código de barras

#### ✅ LoteSerializerTest
- Validación precio_costo > 0
- Validación stock_inicial 1-9999
- Cross-field: fecha_caducidad > fecha_elaboracion

### test_models.py (Validaciones ORM)

#### ✅ ClienteModelTest
- Test clean() con RUT válido/inválido
- Test formato RUT con/sin puntos
- Test RUT con K mayúscula/minúscula

#### ✅ ProductoModelTest
- Test clean() con precio_venta positivo/negativo
- Test costo_unitario >= 0
- Test stock_minimo >= 0

#### ✅ LoteModelTest
- Test clean() con fechas válidas/inválidas
- Test precio_costo > 0
- Test stock_inicial en rango 0-9999
- Test cross-field: fecha_caducidad > fecha_elaboracion
- Test update_fields no valida clean()

## 📈 Cobertura de Pruebas

Las pruebas cubren las 3 capas de validación:

### Capa 1: Validators (pos/validators.py)
✅ 15+ funciones de validación
- Validadores de formato (RUT, teléfono, email)
- Validadores numéricos (precios, stock)
- Validadores de fechas
- Validadores de unicidad

### Capa 2: Serializers (pos/serializers.py)
✅ 7+ serializers principales
- PagoInputSerializer
- VentaInputSerializer
- ClienteSerializer
- EmpleadoCreateSerializer
- ProductoSerializer
- LoteSerializer

### Capa 3: Modelos (pos/models.py)
✅ 3 modelos con clean()
- Cliente (validación RUT)
- Producto (validación precios y stock)
- Lote (validación fechas cross-field)

## 🎯 Resultados Esperados

Al ejecutar todas las pruebas, deberías ver:

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
..................................................................
----------------------------------------------------------------------
Ran 66 tests in 2.345s

OK
Destroying test database for alias 'default'...
```

## 🐛 Troubleshooting

### Error: "No module named 'pos.tests'"
**Solución:** Asegúrate de que existe `pos/tests/__init__.py`

### Error: "django.db.utils.ProgrammingError"
**Solución:** Ejecuta las migraciones antes de las pruebas:
```bash
python manage.py migrate
```

### Las pruebas fallan con "ValidationError not raised"
**Solución:** Verifica que los validadores estén importados correctamente en serializers.py

## 📝 Agregar Nuevas Pruebas

Para agregar nuevas pruebas:

1. Edita el archivo de pruebas correspondiente
2. Crea una nueva clase de prueba:
```python
class NuevaValidacionTest(TestCase):
    def test_caso_valido(self):
        # Tu prueba aquí
        pass

    def test_caso_invalido(self):
        # Tu prueba aquí
        pass
```

3. Ejecuta solo esa prueba:
```bash
python manage.py test pos.tests.test_validators.NuevaValidacionTest
```

## 📚 Recursos Adicionales

- [Django Testing](https://docs.djangoproject.com/en/5.2/topics/testing/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
