@echo off
REM Script para ejecutar todas las pruebas del proyecto Forneria
REM Backend (Django) y Frontend (React + Vite)

echo ========================================
echo   FORNERIA - EJECUCION DE PRUEBAS
echo   Sistema de 3 Capas de Validacion
echo ========================================
echo.

REM Colores para Windows
set GREEN=[92m
set RED=[91m
set YELLOW=[93m
set NC=[0m

echo %YELLOW%[1/2] Ejecutando pruebas del BACKEND (Django)...%NC%
echo ----------------------------------------
cd /d C:\Users\saemm\OneDrive\Documentos\GitHub\Forneria2

REM Ejecutar pruebas Django
python manage.py test pos.tests -v 2

if %ERRORLEVEL% EQU 0 (
    echo %GREEN%✓ Pruebas del backend completadas exitosamente%NC%
) else (
    echo %RED%✗ Algunas pruebas del backend fallaron%NC%
    set BACKEND_FAILED=1
)

echo.
echo.
echo %YELLOW%[2/2] Ejecutando pruebas del FRONTEND (React + Yup)...%NC%
echo ----------------------------------------
cd /d C:\Users\saemm\OneDrive\Documentos\GitHub\Forneria-frontend2

REM Ejecutar pruebas Vitest
call npm test -- --run

if %ERRORLEVEL% EQU 0 (
    echo %GREEN%✓ Pruebas del frontend completadas exitosamente%NC%
) else (
    echo %RED%✗ Algunas pruebas del frontend fallaron%NC%
    set FRONTEND_FAILED=1
)

echo.
echo ========================================
echo   RESUMEN DE PRUEBAS
echo ========================================

if defined BACKEND_FAILED (
    echo %RED%Backend: FALLIDO%NC%
) else (
    echo %GREEN%Backend: EXITOSO%NC%
)

if defined FRONTEND_FAILED (
    echo %RED%Frontend: FALLIDO%NC%
) else (
    echo %GREEN%Frontend: EXITOSO%NC%
)

echo.
if defined BACKEND_FAILED (
    exit /b 1
)
if defined FRONTEND_FAILED (
    exit /b 1
)

echo %GREEN%¡Todas las pruebas pasaron!%NC%
exit /b 0
