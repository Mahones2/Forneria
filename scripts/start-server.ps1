param(
    [switch]$CopyFiles = $false,
    [int]$Port = 8000
)

# Script auxiliar para copiar recursos del landing y arrancar el servidor de desarrollo.
# Uso:
#   .\scripts\start-server.ps1 -CopyFiles  (copia styles e imágenes al static local) 
#   .\scripts\start-server.ps1               (solo arranca runserver)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$landingSrc = 'C:\Users\maeva\OneDrive\Documentos\GitHub\landing_forneria'

Write-Host "Repo root: $repoRoot"
Write-Host "Landing source: $landingSrc"

if ($CopyFiles) {
    if (-Not (Test-Path $landingSrc)) {
        Write-Error "El directorio de landing no existe: $landingSrc"
        exit 1
    }

    $dstCss = Join-Path $repoRoot 'static\css\landing_forneria'
    $dstImages = Join-Path $repoRoot 'static\images\landing_forneria'

    New-Item -ItemType Directory -Path $dstCss -Force | Out-Null
    New-Item -ItemType Directory -Path $dstImages -Force | Out-Null

    # Copiar styles.css si existe
    $srcCss = Join-Path $landingSrc 'styles.css'
    if (Test-Path $srcCss) {
        Copy-Item -Path $srcCss -Destination (Join-Path $dstCss 'styles.css') -Force
        Write-Host "Copiado styles.css -> $dstCss"
    } else {
        Write-Host "No se encontró styles.css en $landingSrc"
    }

    # Copiar imágenes (todas) si existe la carpeta images
    $srcImages = Join-Path $landingSrc 'images'
    if (Test-Path $srcImages) {
        Copy-Item -Path (Join-Path $srcImages '*') -Destination $dstImages -Recurse -Force
        Write-Host "Copiadas imágenes -> $dstImages"
    } else {
        Write-Host "No se encontró carpeta images en $landingSrc"
    }
}

Write-Host "Arrancando servidor Django en puerto $Port... (Ctrl+C para detener)"
# Ejecutar con el python del entorno; usar `py` que suele estar instalado en Windows
& py -3 manage.py runserver "0.0.0.0:$Port"
