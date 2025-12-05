from .settings import *
from pathlib import Path

# Si `BASE_DIR` no está definido en settings.py, crearlo aquí como fallback
try:
    BASE_DIR
except NameError:
    BASE_DIR = Path(__file__).resolve().parent.parent

# Desarrollo local: usar SQLite para poder levantar la aplicación sin MySQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Ajustes convenientes para desarrollo
# En entornos locales normalmente DEBUG=True para poder servir archivos
# estáticos con el servidor de desarrollo y ver errores detallados.
# IMPORTANTE: no dejes DEBUG=True en producción.
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Evitar sobrescribir secretos de producción aquí. Usa este archivo solo en desarrollo local.

# Ajustes de autenticación para desarrollo
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/pos/sistema/'