# Shared readiness and process-ownership checks. Never stop an unrelated server.
function Assert-CurriculumBackend {
    param([string]$Url, [string]$AppRoot, [switch]$IdentityOnly)
    $health = Invoke-RestMethod "$Url/api/health" -TimeoutSec 5
    $expectedModule = [IO.Path]::GetFullPath((Join-Path $AppRoot 'scr/ocr_system/lab8b_curriculum_db.py'))
    if (-not $health.lab8b_module -or -not [string]::Equals(
        [IO.Path]::GetFullPath($health.lab8b_module), $expectedModule, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'A different application folder is serving this port.'
    }
    if ($IdentityOnly) { return }
    if ($health.queryable_database_count -lt 1) { throw 'No queryable databases. Build/import data before starting.' }
    if (-not $health.ollama_ready) { throw "Ollama or the configured model ($($health.model)) is unavailable." }
}

function Save-CurriculumProcess {
    param([int]$Port, [string]$AppRoot)
    $owners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
        Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -ne 1) { throw 'Unable to establish a unique backend process.' }
    $process = Get-Process -Id $owners[0] -ErrorAction Stop
    $logFolder = Join-Path $AppRoot 'work/web'
    New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
    @{ pid = $process.Id; started_ticks = $process.StartTime.ToUniversalTime().Ticks; port = $Port } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logFolder "process-$Port.json") -Encoding utf8
}
