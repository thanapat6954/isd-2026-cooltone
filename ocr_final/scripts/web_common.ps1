# Shared readiness and process-ownership checks. Never stop an unrelated server.
function Get-CurriculumHealth {
    param([string]$Url, [int]$TimeoutSec = 5)
    # Windows PowerShell 5.1 can use ANSI for JSON without a charset header.
    $response = Invoke-WebRequest "$Url/api/health" -UseBasicParsing -TimeoutSec $TimeoutSec
    $json = [Text.Encoding]::UTF8.GetString($response.RawContentStream.ToArray())
    return ($json | ConvertFrom-Json)
}

function Assert-CurriculumBackend {
    param([string]$Url, [string]$AppRoot, [switch]$IdentityOnly)
    $health = Get-CurriculumHealth -Url $Url
    $expectedModule = [IO.Path]::GetFullPath((Join-Path $AppRoot 'scr/ocr_system/lab8b_curriculum_db.py'))
    if (-not $health.lab8b_module -or -not [string]::Equals(
        [IO.Path]::GetFullPath($health.lab8b_module), $expectedModule, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'A different application folder is serving this port.'
    }
    if ($IdentityOnly) { return }
    $expectedCount = 14
    if ($health.build_contract.kind -eq 'academic-plan-only' -and $health.build_contract.partial -eq $true) {
        $expectedCount = @($health.build_contract.profiles).Count
        if ($expectedCount -lt 1 -or $health.expected_database_count -ne $expectedCount) { throw 'declared scope ไม่ถูกต้อง' }
    }
    if ($health.queryable_database_count -ne $expectedCount) { throw 'ฐานข้อมูลไม่ครบตาม scope: restore runtime-data ด้วย scripts/runtime_bundle.py หรือ rollback build ก่อนเริ่มแอป' }
    if (-not $health.ollama_ready) { throw "Ollama/model ไม่พร้อม: เปิด Ollama แล้วรัน ollama pull $($health.model); Mode A ไม่ต้องมี OCR model" }
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
