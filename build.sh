#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Cargar datos iniciales si la BD está vacía
# NOTA: Comentado temporalmente por error de codificación UTF-8
# echo "Verificando si hay datos en la base de datos..."
# python manage.py shell -c "
# from pos.models import Producto
# if Producto.objects.count() == 0:
#     print('Base de datos vacía. Cargando datos iniciales...')
#     import os
#     os.system('python manage.py loaddata datos_produccion.json')
# else:
#     print('Ya hay datos en la base de datos. Saltando carga inicial.')
# "

# Crear superusuario si no existe (usando variables de entorno)
echo "Creando superusuario si no existe..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superusuario {username} creado exitosamente.')
else:
    print(f'Superusuario {username} ya existe.')
"
