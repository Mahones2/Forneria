#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Añadir la raíz del proyecto al path para que Python encuentre el paquete `forneria`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings_dev')
import django
django.setup()

from django.contrib.auth import get_user_model

def main():
    User = get_user_model()
    username = os.environ.get('DJANGO_ADMIN_USER') or (sys.argv[1] if len(sys.argv) > 1 else 'admin')
    email = os.environ.get('DJANGO_ADMIN_EMAIL') or (sys.argv[2] if len(sys.argv) > 2 else 'admin@example.com')
    password = os.environ.get('DJANGO_ADMIN_PASSWORD') or (sys.argv[3] if len(sys.argv) > 3 else None)

    if not password:
        print('ERROR: No password provided. Set DJANGO_ADMIN_PASSWORD env var or pass it as arg 3')
        sys.exit(1)

    user, created = User.objects.get_or_create(username=username, defaults={'email': email})
    user.email = email
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password)
    user.save()

    if created:
        print(f'Created superuser: {username}')
    else:
        print(f'Updated superuser: {username}')

if __name__ == '__main__':
    main()
