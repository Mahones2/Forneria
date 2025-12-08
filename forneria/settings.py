from pathlib import Path
from datetime import timedelta
import os

# ==========================================
# 1. PATHS DE PROYECTO
# ==========================================

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')


# ==========================================
# 2. SEGURIDAD Y DEPURACIÓN (SECURITY & DEBUG)
# ==========================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-2hvq+3_ztv+_dsrnw%b)&a$s&&0yqb!@p3d!)in(d&-_s-oip^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Configuración de CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite
    "http://localhost:3000",  # CRA
]


# ==========================================
# 3. DEFINICIÓN DE APLICACIONES (APPS)
# ==========================================

INSTALLED_APPS = [
    # Core Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-Party Apps (REST Framework, Auth & Docs)
    'corsheaders',
    'rest_framework',
    'django_filters',
    'rest_framework_simplejwt',
    'dj_rest_auth',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    
    # Local Apps
    'pos',
    'inventario',
    'pedido'
]


# ==========================================
# 4. MIDDLEWARE
# ==========================================

MIDDLEWARE = [
    # Terceros (Debe ir primero para manejar solicitudes pre-vuelo)
    'corsheaders.middleware.CorsMiddleware',
    
    # Django Core Middlewares
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
# 6. BASE DE DATOS (DATABASE)
# ==========================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'forneria',
        'USER': 'root',
        'PASSWORD': 'REACH',  
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# ==========================================
# 7. VALIDACIÓN DE CONTRASEÑAS
# ==========================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
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
    # Documentación
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    # Seguridad
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated', # Requiere autenticación por defecto
    ],
}

# Configuración de drf-spectacular (OpenAPI/Swagger)
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

# Configuración de Simple JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",)
}

# Configuración de dj-rest-auth
REST_AUTH = {
    'USE_JWT': True,
    'TOKEN_MODEL': None, # Importante cuando se usa JWT
    'JWT_AUTH_COOKIE': 'djangojwtauth_cookie',
    'JWT_AUTH_REFRESH_COOKIE': 'djangojwtauth_refresh_cookie',
}

# Serializadores personalizados para dj-rest-auth (si aplica)
REST_AUTH_SERIALIZERS = {
    'JWT_SERIALIZER': 'pos.serializers.CustomJWTSerializer',
}