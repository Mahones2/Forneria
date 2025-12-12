#!/bin/bash

echo "========================================"
echo "  CONFIGURACION AUTOMATICA - BACKEND"
echo "========================================"
echo ""

echo "[1/7] Creando entorno virtual..."
python3 -m venv env
if [ $? -ne 0 ]; then
    echo "ERROR: No se pudo crear el entorno virtual"
    exit 1
fi

echo "[2/7] Instalando dependencias..."
env/bin/pip install asgiref attrs certifi charset-normalizer coreschema dj-rest-auth Django django-allauth django-cors-headers django-filter djangorestframework djangorestframework_simplejwt drf-spectacular drf-spectacular-sidecar idna inflection itypes Jinja2 jsonschema jsonschema-specifications MarkupSafe pillow PyJWT PyYAML referencing requests rpds-py setuptools sqlparse tzdata uritemplate urllib3 dj-database-url typing-extensions
if [ $? -ne 0 ]; then
    echo "ERROR: No se pudieron instalar las dependencias"
    exit 1
fi

echo "[3/7] Creando archivo .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "DEBUG=True" >> .env
    echo "SECRET_KEY=django-insecure-dev-key-local" >> .env
    echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> .env
fi

echo "[4/7] Ejecutando migraciones..."
env/bin/python manage.py migrate

echo "[5/7] Creando superusuario admin..."
export PYTHONIOENCODING=utf-8
env/bin/python create_superuser.py

echo "[6/7] Cargando datos de prueba..."
env/bin/python load_initial_data.py

echo ""
echo "========================================"
echo "  CONFIGURACION COMPLETADA!"
echo "========================================"
echo ""
echo "Usuario: admin"
echo "Password: admin123"
echo ""
echo "Para ejecutar el servidor:"
echo "  ./run.sh"
echo ""
