# Configuración Local - Backend

## Instalación Rápida

### Windows
```bash
setup.bat
```

### Mac/Linux
```bash
chmod +x setup.sh
./setup.sh
```

## Ejecutar Servidor

### Windows
```bash
run.bat
```

### Mac/Linux
```bash
chmod +x run.sh
./run.sh
```

## Credenciales

- **Usuario:** admin
- **Contraseña:** admin123

## URL

Backend: http://127.0.0.1:8000

## Notas

- Los scripts crean automáticamente el entorno virtual, instalan dependencias, configuran la base de datos y cargan datos de prueba
- Se usa SQLite para desarrollo local (no necesitas PostgreSQL)
- El archivo `.env` se crea automáticamente con configuración para desarrollo
