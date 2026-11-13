<#
==============================================================================
Crypto AI Agent Platform - Orquestador de Inicio Unificado (Windows PowerShell)
==============================================================================
Inicia los servicios en el orden correcto de dependencias:
  1. MinIO Data Lake (Docker S3)
  2. Inicialización de buckets y políticas (minio-init)
  3. Servidor Backend FastAPI (DuckDB OLAP + Agente Arca en puerto 8001)
  4. Servidor Frontend Next.js 15 (Lightweight Charts UI en puerto 3000)

Maneja apagado graceful sin tocar procesos ajenos ni destruir volúmenes.
==============================================================================
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rootDir

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "        CRYPTO AI AGENT PLATFORM - ORQUESTADOR (WINDOWS)           " -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# 0. Cargar variables de entorno respetando configuración existente
# ------------------------------------------------------------------------------
$envPath = Join-Path $rootDir ".env"
$envExamplePath = Join-Path $rootDir ".env.example"

if (Test-Path $envPath) {
    Write-Host "[OK] Archivo .env detectado. Cargando variables de configuración..." -ForegroundColor Green
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and ($line -match "^([^=]+)=(.*)$")) {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} elseif (Test-Path $envExamplePath) {
    Write-Host "[AVISO] No se detectó .env. Creando .env a partir de .env.example..." -ForegroundColor Yellow
    Copy-Item $envExamplePath $envPath
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and ($line -match "^([^=]+)=(.*)$")) {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Host "[AVISO] No se encontró .env ni .env.example. Usando valores predeterminados." -ForegroundColor Yellow
}

$apiHost = if ($env:API_HOST) { $env:API_HOST } else { "0.0.0.0" }
$apiPort = if ($env:API_PORT) { [int]$env:API_PORT } else { 8001 }
$minioPort = if ($env:MINIO_PORT) { [int]$env:MINIO_PORT } else { 9000 }
$minioConsolePort = if ($env:MINIO_CONSOLE_PORT) { [int]$env:MINIO_CONSOLE_PORT } else { 9001 }
$frontendPort = if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 3000 }

$ollamaBaseUrl = if ($env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL.TrimEnd('/') } else { "http://localhost:11434" }
$ollamaModel = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "llama3.2:3b" }
$groqApiKey = if ($env:GROQ_API_KEY) { $env:GROQ_API_KEY } else { "" }
$groqModel = if ($env:GROQ_MODEL) { $env:GROQ_MODEL } else { "llama-3.3-70b-versatile" }

$nextPublicApiUrl = if ($env:NEXT_PUBLIC_API_URL) { $env:NEXT_PUBLIC_API_URL } else { "http://localhost:$apiPort" }
$env:NEXT_PUBLIC_API_URL = $nextPublicApiUrl

# ------------------------------------------------------------------------------
# 1. Comprobar requisitos del sistema
# ------------------------------------------------------------------------------
Write-Host "`n[Paso 1/4] Verificando requisitos del sistema..." -ForegroundColor Yellow

# Python >= 3.11
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} else {
    Write-Host "[ERROR] Python no está instalado o no se encuentra en el PATH." -ForegroundColor Red
    exit 1
}

$pyVer = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pyMajor = [int](& $pythonCmd -c "import sys; print(sys.version_info.major)")
$pyMinor = [int](& $pythonCmd -c "import sys; print(sys.version_info.minor)")

if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 11)) {
    Write-Host "[ERROR] Se requiere Python 3.11 o superior. Versión detectada: Python $pyVer." -ForegroundColor Red
    exit 1
}
Write-Host "  * Python: OK (v$pyVer)" -ForegroundColor Green

# Node.js y npm
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js no está instalado o no se encuentra en el PATH." -ForegroundColor Red
    exit 1
}
$nodeVer = & node -v
Write-Host "  * Node.js: OK ($nodeVer)" -ForegroundColor Green

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] npm no está instalado." -ForegroundColor Red
    exit 1
}
$npmVer = & npm -v
Write-Host "  * npm: OK (v$npmVer)" -ForegroundColor Green

# Docker y Docker Compose
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker Desktop no está instalado o no se encuentra en el PATH." -ForegroundColor Red
    exit 1
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] El daemon de Docker Desktop no está en ejecución. Por favor inicia Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "  * Docker Desktop: OK (daemon activo)" -ForegroundColor Green

# Inferencia: Groq y Ollama
Write-Host "`nEvaluando proveedores de inferencia de IA..." -ForegroundColor Yellow
$aiAvailable = $false

if ($groqApiKey) {
    Write-Host "  * Groq Cloud: Configurado ($groqModel)" -ForegroundColor Green
    $aiAvailable = $true
} else {
    Write-Host "  * Groq Cloud: No configurado (GROQ_API_KEY vacía en .env)" -ForegroundColor Yellow
}

try {
    $ollamaResp = Invoke-RestMethod -Uri "$ollamaBaseUrl/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
    $foundModel = $false
    if ($ollamaResp.models) {
        foreach ($m in $ollamaResp.models) {
            if ($m.name -eq $ollamaModel -or $m.model -eq $ollamaModel) {
                $foundModel = $true
                break
            }
        }
    }
    if ($foundModel) {
        Write-Host "  * Ollama Local: Disponible con modelo '$ollamaModel'" -ForegroundColor Green
        $aiAvailable = $true
    } else {
        Write-Host "  * Ollama Local: Servicio activo pero el modelo '$ollamaModel' no está descargado." -ForegroundColor Yellow
        Write-Host "    Para descargarlo ejecuta: ollama pull $ollamaModel" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  * Ollama Local: No responde en $ollamaBaseUrl" -ForegroundColor Yellow
}

if (-not $aiAvailable) {
    Write-Host "  * [AVISO - MODO DEGRADADO] Ni Groq ni Ollama cuentan con modelos listos." -ForegroundColor Yellow
    Write-Host "    El sistema operará con el Respaldo Determinista cuantitativo sin IA." -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# 2. Comprobar conflictos de puertos
# ------------------------------------------------------------------------------
function Test-PortOpen {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $waitHandle = $asyncResult.AsyncWaitHandle.WaitOne(300, $false)
        if ($waitHandle -and $client.Connected) {
            $client.EndConnect($asyncResult)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

if (Test-PortOpen -Port $minioPort) {
    $runningCryptoMinio = docker ps --filter "name=crypto-minio" --filter "status=running" --format "{{.Names}}" 2>$null
    if (-not $runningCryptoMinio) {
        Write-Host "[ERROR] El puerto $minioPort (MinIO) ya está ocupado por otro servicio ajeno." -ForegroundColor Red
        Write-Host "Por favor libera el puerto o cambia MINIO_PORT en tu archivo .env." -ForegroundColor Red
        exit 1
    }
}

if (Test-PortOpen -Port $apiPort) {
    Write-Host "[ERROR] El puerto $apiPort (Backend FastAPI) ya está ocupado por otro proceso." -ForegroundColor Red
    Write-Host "Por favor libera el puerto o cambia API_PORT en tu archivo .env." -ForegroundColor Red
    exit 1
}

if (Test-PortOpen -Port $frontendPort) {
    Write-Host "[ERROR] El puerto $frontendPort (Frontend Next.js) ya está ocupado por otro proceso." -ForegroundColor Red
    Write-Host "Por favor libera el puerto o cambia FRONTEND_PORT en tu archivo .env." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------------------
# 3. Iniciar MinIO Data Lake y minio-init
# ------------------------------------------------------------------------------
Write-Host "`n[Paso 2/4] Iniciando MinIO Data Lake e inicializador..." -ForegroundColor Yellow
docker compose up -d minio

Write-Host "Esperando a que MinIO S3 responda en http://localhost:$minioPort/minio/health/live..."
$minioRetries = 20
$minioReady = $false
for ($i = 0; $i -lt $minioRetries; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:$minioPort/minio/health/live" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $minioReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($minioReady) {
    Write-Host "[OK] MinIO S3 activo y saludable en http://localhost:$minioPort" -ForegroundColor Green
} else {
    Write-Host "[ERROR] MinIO no respondió tras $minioRetries segundos. Abortando inicio." -ForegroundColor Red
    exit 1
}

Write-Host "Inicializando buckets y políticas con minio-init..."
docker compose up minio-init

# ------------------------------------------------------------------------------
# 4. Iniciar Backend FastAPI
# ------------------------------------------------------------------------------
Write-Host "`n[Paso 3/4] Iniciando Backend FastAPI (DuckDB + Agente Arca)..." -ForegroundColor Yellow

$venvDir = Join-Path $rootDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvUvicorn = Join-Path $venvDir "Scripts\uvicorn.exe"

if (-not (Test-Path $venvDir)) {
    Write-Host "Creando entorno virtual Python (.venv)..." -ForegroundColor Yellow
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv venv .venv
        & uv pip install -e ".[dev]"
    } else {
        & $pythonCmd -m venv .venv
        & $venvPython -m pip install --upgrade pip
        & $venvPython -m pip install -e ".[dev]"
    }
}

if (-not (Test-Path $venvUvicorn)) {
    Write-Host "Instalando dependencias faltantes en .venv..." -ForegroundColor Yellow
    & $venvPython -m pip install -e ".[dev]"
}

# Variables de seguimiento de procesos hijos para cierre limpio
$backendProc = $null
$frontendProc = $null

try {
    $backendArgs = "backend.app.main:app --host $apiHost --port $apiPort --reload"
    $backendProc = Start-Process -FilePath $venvUvicorn -ArgumentList $backendArgs -PassThru -NoNewWindow

    Write-Host "Esperando disponibilidad del backend en http://localhost:$apiPort/health..."
    $backendRetries = 25
    $backendReady = $false
    for ($i = 0; $i -lt $backendRetries; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:$apiPort/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                $backendReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    if ($backendReady) {
        Write-Host "[OK] Backend FastAPI operativo en http://localhost:$apiPort" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Backend FastAPI no respondió en el tiempo límite en el puerto $apiPort." -ForegroundColor Red
        throw "Fallo al iniciar el backend FastAPI."
    }

    # --------------------------------------------------------------------------
    # 5. Iniciar Frontend Next.js 15
    # --------------------------------------------------------------------------
    Write-Host "`n[Paso 4/4] Iniciando Frontend Next.js 15..." -ForegroundColor Yellow
    $frontendDir = Join-Path $rootDir "frontend"
    $nodeModulesDir = Join-Path $frontendDir "node_modules"

    if (-not (Test-Path $nodeModulesDir)) {
        Write-Host "Instalando dependencias de Node.js en frontend/..." -ForegroundColor Yellow
        Push-Location $frontendDir
        & npm install
        Pop-Location
    }

    $frontendArgs = "run dev -- -p $frontendPort"
    $frontendProc = Start-Process -FilePath "npm" -ArgumentList $frontendArgs -WorkingDirectory $frontendDir -PassThru -NoNewWindow

    Write-Host "Esperando disponibilidad del frontend en http://localhost:$frontendPort..."
    $frontendRetries = 30
    $frontendReady = $false
    for ($i = 0; $i -lt $frontendRetries; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:$frontendPort" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($resp.StatusCode -eq 200 -or $resp.StatusCode -eq 304) {
                $frontendReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    if ($frontendReady) {
        Write-Host "[OK] Frontend Next.js 15 activo en http://localhost:$frontendPort" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Frontend no respondió en el puerto $frontendPort tras $frontendRetries s." -ForegroundColor Red
        throw "Fallo al iniciar el Frontend Next.js."
    }

    Write-Host "`n===================================================================" -ForegroundColor Green
    Write-Host "             SISTEMA COMPLETO EN LÍNEA Y VERIFICADO               " -ForegroundColor Green
    Write-Host "===================================================================" -ForegroundColor Green
    Write-Host "  * Frontend UI:            http://localhost:$frontendPort" -ForegroundColor Cyan
    Write-Host "  * Backend REST & Chat:    http://localhost:$apiPort" -ForegroundColor Cyan
    Write-Host "  * Documentación Swagger:  http://localhost:$apiPort/docs" -ForegroundColor Cyan
    Write-Host "  * Salud del Sistema:      http://localhost:$apiPort/health" -ForegroundColor Cyan
    Write-Host "  * MinIO S3 API:           http://localhost:$minioPort" -ForegroundColor Cyan
    Write-Host "  * MinIO S3 Console:       http://localhost:$minioConsolePort (minioadmin / miniopassword123)" -ForegroundColor Cyan
    Write-Host "-------------------------------------------------------------------"
    Write-Host "Presiona Ctrl+C para detener los servicios de forma limpia." -ForegroundColor Yellow
    Write-Host "===================================================================`n" -ForegroundColor Green

    # Mantener el script vivo esperando a que el usuario presione Ctrl+C o algún proceso termine
    while ($true) {
        if ($backendProc.HasExited) {
            Write-Host "[AVISO] El proceso del backend terminó inesperadamente." -ForegroundColor Red
            break
        }
        if ($frontendProc.HasExited) {
            Write-Host "[AVISO] El proceso del frontend terminó inesperadamente." -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host "`n[Apagado] Deteniendo únicamente los procesos iniciados por el orquestador..." -ForegroundColor Yellow
    if ($backendProc -and -not $backendProc.HasExited) {
        Write-Host "  * Deteniendo Backend (PID $($backendProc.Id))..."
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Write-Host "  * Deteniendo Frontend (PID $($frontendProc.Id))..."
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[OK] Procesos detenidos correctamente. (Los volúmenes y contenedores no fueron destruidos)." -ForegroundColor Green
}
