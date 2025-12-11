from pathlib import Path
from datetime import timedelta
import os
import dj_database_url

# ==========================================
# 1. PATHS DE PROYECTO
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')


# ==========================================
# 2. SEGURIDAD Y DEPURACIÓN (SECURITY & DEBUG)
# ==========================================

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-2hvq+3_ztv+_dsrnw%b)&a$s&&0yqb!@p3d!)in(d&-_s-oip^')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# CORS - Permitir localhost para desarrollo y dominio de Vercel para producción
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite desarrollo
    "http://localhost:3000",  # CRA desarrollo
]

# Agregar dominio de Vercel si está configurado
VERCEL_URL = os.environ.get('VERCEL_URL', '')
if VERCEL_URL:
    CORS_ALLOWED_ORIGINS.append(f"https://{VERCEL_URL}")

# Permitir todos los orígenes en producción si CORS_ALLOW_ALL está activado
if os.environ.get('CORS_ALLOW_ALL', 'False') == 'True':
    CORS_ALLOW_ALL_ORIGINS = True


# ==========================================
# 3. DEFINICIÓN DE APLICACIONES (APPS)
# ==========================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'django_filters',
    'rest_framework_simplejwt',
    'dj_rest_auth',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    
    'pos',
    'inventario',
    'pedido'
]


# ==========================================
# 4. MIDDLEWARE
# ==========================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir archivos estáticos en producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ==========================================
# 5. CONFIGURACIÓN DE URLS Y TEMPLATES
# ==========================================

ROOT_URLCONF = 'forneria.urls'
WSGI_APPLICATION = 'forneria.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ==========================================
# 6. BASE DE DATOS (DATABASE)
# ==========================================

# Usar PostgreSQL en producción (Railway), SQLite en desarrollo
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Producción - PostgreSQL desde Railway
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Desarrollo - SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ==========================================
# 7. VALIDACIÓN DE CONTRASEÑAS
# ==========================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==========================================
# 8. INTERNACIONALIZACIÓN (I18N)
# ==========================================

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True


# ==========================================
# 9. ARCHIVOS ESTÁTICOS Y DEFAULTS
# ==========================================

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Para producción (collectstatic)
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] if os.path.exists(os.path.join(BASE_DIR, 'static')) else []

# Configuración de WhiteNoise para comprimir y cachear archivos estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==========================================
# 10. CONFIGURACIÓN DE REST FRAMEWORK (DRF)
# ==========================================

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Mi API',
    'DESCRIPTION': 'Documentación de mi API con drf-spectacular',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
    },
}


# ==========================================
# 11. AUTENTICACIÓN JWT (SIMPLE JWT & DJ-REST-AUTH)
# ==========================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",)
}

REST_AUTH = {
    'USE_JWT': True,
    'TOKEN_MODEL': None,
    'JWT_AUTH_COOKIE': 'djangojwtauth_cookie',
    'JWT_AUTH_REFRESH_COOKIE': 'djangojwtauth_refresh_cookie',
}

REST_AUTH_SERIALIZERS = {
    'JWT_SERIALIZER': 'pos.serializers.CustomJWTSerializer',
}
