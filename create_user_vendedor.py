#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from django.contrib.auth.models import User
from pos.models import Empleado

# Crear usuario vendedor
try:
    # Eliminar si existe
    try:
        user = User.objects.get(username='vendedor')
        user.delete()
        print('[INFO] Usuario vendedor anterior eliminado')
    except User.DoesNotExist:
        pass

    # Crear nuevo usuario
    user = User.objects.create_user(
        username='vendedor',
        password='vendedor123',
        email='vendedor@forneria.cl',
        first_name='Juan',
        last_name='Perez'
    )
    print(f'[OK] Usuario creado: {user.username}')
    print(f'     Email: {user.email}')
    print(f'     Nombre: {user.first_name} {user.last_name}')

    # Crear empleado asociado
    empleado = Empleado.objects.create(
        usuario=user,
        nombres='Juan',
        apellido_paterno='Perez',
        run='22222222-2',
        correo='vendedor@forneria.cl',
        fono=987654321,
        clave='vendedor123',
        direccion='Avenida Central 456',
        cargo='Vendedor'
    )
    print(f'[OK] Empleado creado: {empleado.nombres} {empleado.apellido_paterno}')
    print(f'     Cargo: {empleado.cargo}')
    print(f'     RUN: {empleado.run}')
    print('')
    print('=== CREDENCIALES ===')
    print('Username: vendedor')
    print('Password: vendedor123')

except Exception as e:
    print(f'[ERROR] {e}')
    import traceback
    traceback.print_exc()
