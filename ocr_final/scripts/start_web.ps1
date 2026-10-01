param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$pythonPath = Join-Path $appRoot 'venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the project venv and install requirements.txt first.'
}
$url = "http://localhost:$Port"
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    try {
        $schema = Invoke-RestMethod "$url/openapi.json" -TimeoutSec 5
        if ($schema.paths.PSObject.Properties.Name -contains '/ask') {
            Write-Output "Backend already running: $url/frontend/"
            exit 0
        }
    } catch { }
    throw "Port $Port is occupied by another server. Stop that server or choose -Port 8001. Do not use python -m http.server for the API."
}
$logFolder = Join-Path $appRoot 'work/web'
New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
$runTag = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$stdoutPath = Join-Path $logFolder "backend-$runTag.stdout.log"
$stderrPath = Join-Path $logFolder "backend-$runTag.stderr.log"
$env:PYTHONUTF8 = '1'
$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @(
    '-m', 'uvicorn', 'lab10_fastapi.curriculum_app.main:app',
    '--host', '127.0.0.1', '--port', "$Port"
) -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if ($backendProcess.HasExited) { throw "Backend exited. Check $stderrPath" }
    try {
        $schema = Invoke-RestMethod "$url/openapi.json" -TimeoutSec 2
        if (-not ($schema.paths.PSObject.Properties.Name -contains '/ask')) {
            throw 'Unexpected application on the selected port'
        }
        Write-Output "Backend ready: $url/frontend/"
        Write-Output "Logs: $stderrPath"
        exit 0
    } catch { Start-Sleep -Milliseconds 300 }
}
throw "Backend not ready. Check $stderrPath"
