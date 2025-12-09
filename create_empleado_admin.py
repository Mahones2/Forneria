#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from django.contrib.auth.models import User
from pos.models import Empleado

# Buscar usuario admin
try:
    user = User.objects.get(username='admin')
    print(f"[OK] Usuario encontrado: {user.username}")

    # Verificar si ya tiene Empleado
    if hasattr(user, 'empleado'):
        print(f"[OK] Ya tiene Empleado: {user.empleado}")
    else:
        # Crear Empleado
        empleado = Empleado.objects.create(
            usuario=user,
            nombres="Administrador",
            apellido_paterno="Sistema",
            run="11111111-1",
            correo="admin@forneria.cl",
            fono=999999999,
            clave="admin123",  # Este campo no se usa para auth, pero es requerido
            direccion="Oficina Central",
            cargo="Administrador"
        )
        print(f"[OK] Empleado creado: {empleado}")
        print(f"  - Nombre: {empleado.nombres} {empleado.apellido_paterno}")
        print(f"  - Cargo: {empleado.cargo}")
        print(f"  - RUN: {empleado.run}")

except User.DoesNotExist:
    print("[ERROR] Usuario admin no existe")
except Exception as e:
    print(f"[ERROR] {e}")
