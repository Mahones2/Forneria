#!/usr/bin/env python
"""
Script para crear superusuario automáticamente en producción
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from django.contrib.auth import get_user_model

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
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f'✅ Superusuario "{username}" creado exitosamente')

print(f'📧 Email: {email}')
print(f'🔑 Puedes iniciar sesión con: {username} / {password}')
