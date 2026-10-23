<#
.SYNOPSIS
    Start the whole Janus stack with one command: Ollama (if needed), the Python
    engine, then the Go proxy. Ctrl+C stops the engine (and Ollama if this script started it).

.EXAMPLE
    .\scripts\start.ps1
    .\scripts\start.ps1 -SkipOllama
#>
param(
    [switch]$SkipOllama,
    [int]$EngineTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".janusenv\Scripts\python.exe"
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null

if (-not (Test-Path $python)) { throw "Python venv not found at $python" }

# Ports come from .env when present, otherwise the defaults.
$envFile = Join-Path $root ".env"
$engineAddr = "localhost:50051"
if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match '^\s*JANUS_ENGINE_ADDR=(.+)$' } | Select-Object -First 1
    if ($line -match '=(.+)$') { $engineAddr = $Matches[1].Trim() }
}
$enginePort = [int]($engineAddr -split ':')[-1]

$started = @()

function Test-Port([int]$port) {
    $c = New-Object Net.Sockets.TcpClient
    try { $c.Connect("127.0.0.1", $port); return $true } catch { return $false } finally { $c.Dispose() }
}

try {
    # 1. Ollama (Pass 3 judge)
    if (-not $SkipOllama) {
        if (Test-Port 11434) {
            Write-Host "[janus] Ollama already running"
        } else {
            Write-Host "[janus] Starting Ollama..."
            $started += Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput (Join-Path $logDir "ollama.out.log") `
                -RedirectStandardError (Join-Path $logDir "ollama.err.log")
        }
    }

    # 2. Python engine
    if (Test-Port $enginePort) {
        throw "Port $enginePort is already in use. Is the engine already running?"
    }
    Write-Host "[janus] Starting engine (logs in logs\engine.*.log)..."
    $engine = Start-Process $python -ArgumentList "main.py" -WorkingDirectory (Join-Path $root "engine") `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logDir "engine.out.log") `
        -RedirectStandardError (Join-Path $logDir "engine.err.log")
    $started += $engine

    $deadline = (Get-Date).AddSeconds($EngineTimeoutSeconds)
    while (-not (Test-Port $enginePort)) {
        if ($engine.HasExited) { throw "Engine exited early. See logs\engine.err.log" }
        if ((Get-Date) -gt $deadline) { throw "Engine did not open port $enginePort within ${EngineTimeoutSeconds}s" }
        Start-Sleep -Milliseconds 500
    }
    Write-Host "[janus] Engine ready on port $enginePort"

    # 3. Go proxy (foreground)
    Write-Host "[janus] Starting proxy (Ctrl+C to stop)..."
    Push-Location $root
    try { go run ./cmd/janus } finally { Pop-Location }
}
finally {
    foreach ($p in $started) {
        if ($p -and -not $p.HasExited) {
            Write-Host "[janus] Stopping $($p.ProcessName) ($($p.Id))"
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
