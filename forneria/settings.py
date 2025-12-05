from pathlib import Path
import os
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-2hvq+3_ztv+_dsrnw%b)&a$s&&0yqb!@p3d!)in(d&-_s-oip^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'django_filters',
    'dj_rest_auth',
    'pos',
    'inventario',
    'pedido',
    'landing',
    'reportes',
    'analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'forneria.urls'

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
            # Registrar templatetags comunes como builtins evita tener que
            # hacer {% load currency %} en cada plantilla.
            'builtins': [
                'pos.templatetags.currency',
            ],
        },
    },
]

WSGI_APPLICATION = 'forneria.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'forneria_github',
        'USER': 'root',
        'PASSWORD': '',  
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': BASE_DIR / 'db.sqlite3',
#    }
#}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-cl'  

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Añadir carpeta externa de imágenes del landing si existe (no obligatorio copiar archivos).
# Esto permite servir las imágenes desde `c:\Users\maeva\OneDrive\Documentos\GitHub\landing_forneria\images`
# durante desarrollo sin mover los ficheros al proyecto.
EXTERNAL_LANDING_IMAGES = r"C:\Users\maeva\OneDrive\Documentos\GitHub\landing_forneria\images"
if os.path.isdir(EXTERNAL_LANDING_IMAGES):
    STATICFILES_DIRS.append(EXTERNAL_LANDING_IMAGES)

# Agregar todo el directorio del landing como posible fuente de estáticos (contiene styles.css y otros recursos)
EXTERNAL_LANDING_DIR = r"C:\Users\maeva\OneDrive\Documentos\GitHub\landing_forneria"
if os.path.isdir(EXTERNAL_LANDING_DIR):
    STATICFILES_DIRS.append(EXTERNAL_LANDING_DIR)
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# URL a la que redirigir tras login si no hay 'next' en la petición
LOGIN_REDIRECT_URL = '/pos/sistema/'
LOGIN_URL = '/accounts/login/'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',   
        'dj_rest_auth.jwt_auth.JWTCookieAuthentication',        
    ],
}


REST_AUTH = {
    'USE_JWT': True,
    'TOKEN_MODEL': None,  
    'JWT_AUTH_COOKIE': 'djangojwtauth_cookie',
    'JWT_AUTH_REFRESH_COOKIE': 'djangojwtauth_refresh_cookie',
}