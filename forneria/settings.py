from pathlib import Path
from datetime import timedelta
import os

# ==========================================
# 1. PATHS DE PROYECTO
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')


# ==========================================
# 2. SEGURIDAD Y DEPURACIÓN (SECURITY & DEBUG)
# ==========================================

SECRET_KEY = 'django-insecure-2hvq+3_ztv+_dsrnw%b)&a$s&&0yqb!@p3d!)in(d&-_s-oip^'
DEBUG = True
ALLOWED_HOSTS = []

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite
    "http://localhost:3000",  # CRA
]


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
    'pedido',
    'analytics'
]


# ==========================================
# 4. MIDDLEWARE
# ==========================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
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
# 6. BASE DE DATOS (DATABASE) -> SQLITE
# ==========================================

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
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
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
    'USER_DETAILS_SERIALIZER': 'pos.serializers.UserDetailsSerializer',
}
