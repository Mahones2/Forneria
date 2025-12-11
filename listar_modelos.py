import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from django.apps import apps

# Listar todos los modelos disponibles
print("Modelos disponibles en el proyecto:\n")

for app_config in apps.get_app_configs():
    print(f"\n{app_config.name.upper()}:")
    for model in app_config.get_models():
        print(f"  - {model.__name__}")
