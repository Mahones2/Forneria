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

# Crear superusuario
echo "Creando/actualizando superusuario..."
python create_superuser.py
