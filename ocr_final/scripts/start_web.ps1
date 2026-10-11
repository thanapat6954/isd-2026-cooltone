param([ValidateRange(1,65535)][int]$Port = 8000, [ValidateRange(5,120)][int]$StartupTimeoutSeconds = 60)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$pythonPath = Join-Path $appRoot 'venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'From ocr_final, create venv with py -3.11 -m venv venv, then install requirements-web-tested.txt using venv/Scripts/python.exe -m pip.'
}
$url = "http://127.0.0.1:$Port"
$probeUrl = "http://127.0.0.1:$Port"
. (Join-Path $PSScriptRoot 'web_common.ps1')
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    try {
        Assert-CurriculumBackend -Url $probeUrl -AppRoot $appRoot
        Save-CurriculumProcess -Port $Port -AppRoot $appRoot
        Write-Output "Backend already running, database and configured model ready: $url/frontend/"
        exit 0
    } catch {
        throw "Port $Port is occupied; readiness check failed: มีโปรแกรมใช้อยู่ เลือก port ว่างด้วย -Port 8005 และเปิด URL ที่ launcher พิมพ์; ไม่หยุด process อื่น. $($_.Exception.Message)"
    }
}
$logFolder = Join-Path $appRoot 'work/web'
New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
# Fail before spawning when artifacts/models are missing. This never runs OCR.
& $pythonPath -X utf8 (Join-Path $PSScriptRoot 'check_setup.py')
if ($LASTEXITCODE -ne 0) { throw 'ข้อมูลหรือ model ไม่พร้อม: ตรวจรายการข้างบน, restore PDFs/DB และ ollama pull qwen3:4b แล้วลองใหม่' }
$runTag = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$stdoutPath = Join-Path $logFolder "backend-$runTag.stdout.log"
$stderrPath = Join-Path $logFolder "backend-$runTag.stderr.log"
$env:PYTHONUTF8 = '1'
$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @(
    '-m', 'uvicorn', 'lab10_fastapi.curriculum_app.main:app',
    '--host', '127.0.0.1', '--port', "$Port"
) -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
# A cold Python process can take longer than thirty fast connection-refused
# attempts. Use elapsed time, while preserving the API and occupied-port guard.
$startupDeadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
$lastReadinessError = 'No response received'
while ([DateTime]::UtcNow -lt $startupDeadline) {
    if ($backendProcess.HasExited) { throw "Backend exited. Check $stderrPath" }
    try {
        Assert-CurriculumBackend -Url $probeUrl -AppRoot $appRoot
        Save-CurriculumProcess -Port $Port -AppRoot $appRoot
        Write-Output "Backend ready: $url/frontend/"
        Write-Output "Logs: $stderrPath"
        exit 0
    } catch {
        $lastReadinessError = $_.Exception.Message
        Start-Sleep -Milliseconds 300
    }
}
throw "Backend not ready: $lastReadinessError. Check $stderrPath"
