param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot 'web_common.ps1')
$recordPath = Join-Path $appRoot "work/web/process-$Port.json"
if (-not (Test-Path -LiteralPath $recordPath)) { throw 'No verified launch record. Use start_web.ps1 to check the existing server first.' }
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
$process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
if (-not $process) { Write-Output 'Recorded backend is already stopped.'; exit 0 }
if ($process.StartTime.ToUniversalTime().Ticks -ne $record.started_ticks) { throw 'Process ID was reused. Nothing stopped.' }
$owners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique)
if ($owners.Count -ne 1 -or $owners[0] -ne $process.Id) { throw 'Port ownership changed. Nothing stopped.' }
Assert-CurriculumBackend -Url "http://127.0.0.1:$Port" -AppRoot $appRoot -IdentityOnly
Stop-Process -Id $process.Id -ErrorAction Stop
Write-Output "Stopped the verified backend on port $Port. Ollama and databases are unchanged."
