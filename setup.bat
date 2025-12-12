@echo off
echo ========================================
echo   CONFIGURACION AUTOMATICA - BACKEND
echo ========================================
echo.

echo [1/7] Creando entorno virtual...
python -m venv env
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)

echo [2/7] Instalando dependencias...
env\Scripts\pip.exe install asgiref attrs certifi charset-normalizer coreschema dj-rest-auth Django django-allauth django-cors-headers django-filter djangorestframework djangorestframework_simplejwt drf-spectacular drf-spectacular-sidecar idna inflection itypes Jinja2 jsonschema jsonschema-specifications MarkupSafe pillow PyJWT PyYAML referencing requests rpds-py setuptools sqlparse tzdata uritemplate urllib3 dj-database-url typing-extensions
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias
    pause
    exit /b 1
)

echo [3/7] Creando archivo .env...
if not exist .env (
    copy .env.example .env
    echo DEBUG=True >> .env
    echo SECRET_KEY=django-insecure-dev-key-local >> .env
    echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env
)

echo [4/7] Ejecutando migraciones...
env\Scripts\python.exe manage.py migrate

echo [5/7] Creando superusuario admin...
set PYTHONIOENCODING=utf-8
env\Scripts\python.exe create_superuser.py

echo [6/7] Cargando datos de prueba...
env\Scripts\python.exe load_initial_data.py

echo.
echo ========================================
echo   CONFIGURACION COMPLETADA!
echo ========================================
echo.
echo Usuario: admin
echo Password: admin123
echo.
echo Para ejecutar el servidor:
echo   run.bat
echo.
pause
