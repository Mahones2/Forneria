#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Cargar datos iniciales
echo "Cargando datos iniciales..."
python load_initial_data.py

# Crear superusuario
echo "Creando/actualizando superusuario..."
python create_superuser.py
