#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para crear usuario administrador"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from django.contrib.auth.models import User
from pos.models import Empleado

# Credenciales
username = 'admin'
email = 'admin@forneria.cl'
password = 'admin123'

# Crear superusuario si no existe
if not User.objects.filter(username=username).exists():
    user = User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superusuario creado: {username}')

    # Crear empleado asociado
    empleado = Empleado.objects.create(
        user=user,
        rut='11111111-1',
        nombre='Admin',
        apellido='Sistema',
        cargo='Administrador',
        telefono='+56912345678',
        email=email
    )
    print(f'Empleado creado: {empleado.nombre_completo}')
else:
    print(f'Usuario {username} ya existe')
    user = User.objects.get(username=username)
    if hasattr(user, 'empleado'):
        print(f'Empleado: {user.empleado.nombre_completo}')
    else:
        print('Falta crear empleado para este usuario')

print('')
print('=== CREDENCIALES ===')
print(f'Usuario: {username}')
print(f'Contraseña: {password}')
print('====================')
