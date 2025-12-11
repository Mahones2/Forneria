#!/usr/bin/env python
"""
Script para crear superusuario y empleado automáticamente en producción
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from django.contrib.auth import get_user_model
from pos.models import Empleado

User = get_user_model()

# Credenciales del superusuario
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@forneria.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

# Crear o actualizar superusuario
if User.objects.filter(username=username).exists():
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print(f'✅ Superusuario "{username}" actualizado con nueva contraseña')
else:
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f'✅ Superusuario "{username}" creado exitosamente')

# Crear o actualizar Empleado asociado
if not hasattr(user, 'empleado'):
    try:
        empleado = Empleado.objects.create(
            usuario=user,
            run='11111111-1',  # RUN genérico para admin
            fono='+56900000000',  # Teléfono genérico
            direccion='Dirección Administrativa',
            cargo='Administrador'
        )
        print(f'✅ Empleado creado para usuario "{username}"')
    except Exception as e:
        print(f'⚠️  Error al crear empleado: {e}')
        print(f'⚠️  Puedes crearlo manualmente desde /admin/')
else:
    print(f'✅ El empleado ya existe para usuario "{username}"')

print(f'📧 Email: {email}')
print(f'🔑 Puedes iniciar sesión con: {username} / {password}')
