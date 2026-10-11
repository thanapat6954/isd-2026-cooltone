param(
    [ValidateRange(1,65535)][int]$Port = 8026,
    [string]$OutputDir = '',
    [string]$EvidenceDir = '',
    [string]$NodePath = '',
    [ValidateSet('All','Regression')][string]$Suite = 'All',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$pythonPath = Join-Path $appRoot 'venv/Scripts/python.exe'
$url = "http://127.0.0.1:$Port"
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create venv and install requirements-web-tested.txt first.' }
. (Join-Path $PSScriptRoot 'evaluation_node.ps1')
$nodeExe = Resolve-EvaluationNode -NodePath $NodePath
if (-not $CheckOnly) {
    & $pythonPath -X utf8 (Join-Path $PSScriptRoot 'check_evaluation_setup.py')
    if ($LASTEXITCODE -ne 0) { throw 'Install test dependencies: .\venv\Scripts\python.exe -m pip install -r requirements-evaluation-tested.txt' }
}
if (-not $OutputDir) { $OutputDir = Join-Path $env:TEMP ("curriculum-evaluation-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')) }
$OutputDir = [IO.Path]::GetFullPath($OutputDir)
if (Test-Path -LiteralPath $OutputDir) { throw 'OutputDir already exists; choose a new folder.' }
if (-not $EvidenceDir) { $EvidenceDir = Join-Path $appRoot ("evaluation_runs/evaluation-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)) }
$EvidenceDir = [IO.Path]::GetFullPath($EvidenceDir)
if (Test-Path -LiteralPath $EvidenceDir) { throw 'EvidenceDir already exists; choose a new folder.' }
New-Item -ItemType Directory -Path $OutputDir | Out-Null
$jobs = [Collections.Generic.List[object]]::new()
$ownsBackend = $false
$shellBinary = if ($PSVersionTable.PSEdition -eq 'Core') { Join-Path $PSHOME 'pwsh.exe' } else { Join-Path $PSHOME 'powershell.exe' }

function Save-EvaluationSummary {
    [ordered]@{ app_root=$appRoot; url=$url; node_executable=$nodeExe; suite=$Suite; check_only=$CheckOnly.IsPresent; jobs=@($jobs.ToArray()); real_ui_checked=$false } |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputDir 'summary.json') -Encoding UTF8
    $lines = @('# ผล Evaluation ที่รันจริง', '', "Application: $appRoot", "Backend: $url", "Suite: $Suite")
    if ($CheckOnly) { $lines += @('', 'โหมด CheckOnly: ตรวจ Node และ startup เท่านั้น ไม่ได้รัน Evaluation suites') }
    if ($Suite -eq 'Regression') { $lines += @('', 'เลือก Regression: ตรวจพฤติกรรมระบบและตัวทดสอบ ไม่ได้รัน source coverage audit') }
    $lines += @('', '| ชุด | สถานะ | Exit code |', '|---|---|---:|')
    foreach ($job in $jobs) { $lines += "| $($job.name) | $($job.status) | $($job.exit_code) |" }
    $checksPath = Join-Path $OutputDir 'checks/checks.json'
    if (Test-Path -LiteralPath $checksPath) {
        $checks = Get-Content -LiteralPath $checksPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $lines += @('', '## รายละเอียดชุดหลัก', '', '| ชุด | จำนวนที่รายงาน | Exit code |', '|---|---|---:|')
        foreach ($job in $checks.jobs) {
            $count = 'ดู JSON รายข้อ'
            if ($job.name -eq 'unit' -and $job.stderr -match 'Ran (\d+) tests') { $count = "$($Matches[1]) tests" }
            if ($job.name -eq 'schema' -and $job.stdout -match 'ผ่าน\s+(\d+)\s*/\s*ไม่ผ่าน\s+(\d+)') { $count = "$($Matches[1]) pass / $($Matches[2]) fail" }
            if ($job.name -eq 'frontend' -and $job.stdout -match 'tests\s+(\d+)') { $count = "$($Matches[1]) tests" }
            $lines += "| $($job.name) | $count | $($job.exit_code) |"
        }
        $lines += @('', 'ดูจำนวน tests และ stdout/stderr ใน checks/checks.json; เมื่อ main runner หยุด ชุดถัดไปยังไม่ได้ตรวจ')
    }
    foreach ($name in @('gold','old2560','metadata','graduation','counterfactual')) {
        $path = if ($name -in @('gold','old2560')) { Join-Path $OutputDir "checks/$name.json" } else { Join-Path $OutputDir "$name.json" }
        if (Test-Path -LiteralPath $path) {
            try {
                $data = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
                $cases = @($data.cases | Where-Object { $null -ne $_ })
                $passed = @($cases | Where-Object { $_.passed -eq $true }).Count
                $complete = $null -ne $data.summary
                $lines += @('', "- $name : ผ่าน $passed / เก็บผลได้ $($cases.Count) ข้อ; มี final summary: $complete")
            } catch { $lines += @('', "- $name : อ่านผลไม่สำเร็จ; ตรวจ JSON/logs") }
        }
    }
    $lines += @('', '## ขอบเขตและข้อจำกัด', '',
        '- Counterfactual ตรวจ SQLite copies ชั่วคราวและยืนยัน production hashes ไม่เปลี่ยน; ดูผลจริงใน counterfactual.json',
        '- UI 6/6 และ 13/13 ต้องตรวจผ่าน browser จริง แฟ้มนี้ยังไม่ตรวจ UI',
        '- Gold มี missing-evidence/uncertainty cases ไม่ใช่ accuracy ทั้งหนังสือ',
        '- Graduation ตรวจ reference เดิมและทุกแถวเพิ่มเติมกับ source review ที่อนุมัติ ไม่ใช่รับรองสิทธิ์จบ',
        '- Audit findings ไม่ใช่จำนวนคำตอบผิด; ดู audit/ และ audit.stdout.log',
        '- ไม่เปลี่ยน DB, source PDFs, OCR หรือเฉลย และไม่ทำ commit/push')
    $lines | Set-Content -LiteralPath (Join-Path $OutputDir 'REPORT.md') -Encoding UTF8
}

function Invoke-EvaluationJob {
    param([string]$Name, [string[]]$Arguments)
    Write-Host "Running $Name ..."
    $savedPreference = $ErrorActionPreference
    try {
        # Preserve native stderr as evidence without aborting the next suite.
        $ErrorActionPreference = 'Continue'
        & $pythonPath -X utf8 @Arguments 1> (Join-Path $OutputDir "$Name.stdout.log") 2> (Join-Path $OutputDir "$Name.stderr.log")
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
    if ($null -eq $code) { $code = 1 }
    $status = if ($code -eq 0) { 'ผ่าน' } else { 'ไม่ผ่านหรือรันไม่ครบ; ดู logs' }
    $details = $null
    if ($Name -eq 'audit' -and $code -in @(0,1,2)) {
        $auditPath = Join-Path $OutputDir 'audit/audit_results.json'
        if (Test-Path -LiteralPath $auditPath) {
            $audit = Get-Content -LiteralPath $auditPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $findings = @($audit.datasets | ForEach-Object { $_.findings } | Where-Object { $null -ne $_ })
            $failed = @($findings | Where-Object { $_.status -eq 'FAIL' }).Count
            $incomplete = @($findings | Where-Object { $_.status -in @('SKIPPED','NEEDS_REVIEW') }).Count
            $executionErrors = @($findings | Where-Object { $_.check -eq 'dataset_error' }).Count
            $details = [ordered]@{datasets=@($audit.datasets).Count; failed_findings=$failed; incomplete_findings=$incomplete; execution_errors=$executionErrors}
            if ($executionErrors -eq 0) { $status = "ตรวจเสร็จ; พบ FAIL $failed / incomplete $incomplete (ยังไม่รับรองข้อมูลครบ)" }
        }
    }
    $jobs.Add([ordered]@{name=$Name; status=$status; exit_code=$code; arguments=$Arguments; details=$details})
    Save-EvaluationSummary
    Write-Host "$Name : exit $code"
}

Push-Location -LiteralPath $appRoot
try {
    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) {
        & $shellBinary -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'start_web.ps1') -Port $Port
        if ($LASTEXITCODE -ne 0) { throw 'Backend startup failed; see launcher output.' }
        $ownsBackend = $true
    }
    . (Join-Path $PSScriptRoot 'web_common.ps1')
    Assert-CurriculumBackend -Url $url -AppRoot $appRoot
    $health = Get-CurriculumHealth -Url $url -TimeoutSec 10
    if ($health.build_contract.partial -eq $true -or $health.queryable_database_count -ne 14) {
        throw 'This evaluation requires the full 14-DB snapshot from runtime-data.zip (Mode A).'
    }
    $health | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $OutputDir 'health.json') -Encoding UTF8
    if ($CheckOnly) {
        $jobs.Add([ordered]@{name='startup-only'; status='Node/backend/14-DB readiness ผ่าน; ไม่ได้รัน tests'; exit_code=0})
    } else {
        Invoke-EvaluationJob -Name 'checks' -Arguments @('scripts/run_handoff_checks.py','--app-root',$appRoot,'--url',$url,'--output',(Join-Path $OutputDir 'checks'))
        Invoke-EvaluationJob -Name 'metadata' -Arguments @('scripts/verify_program_metadata.py','--url',$url,'--output',(Join-Path $OutputDir 'metadata.json'))
        Invoke-EvaluationJob -Name 'graduation' -Arguments @('scripts/run_requirement_qa.py','--app-root',$appRoot,'--url',$url,'--output',(Join-Path $OutputDir 'graduation.json'))
        Invoke-EvaluationJob -Name 'counterfactual' -Arguments @('scripts/verify_requirement_isolation.py','--app-root',$appRoot,'--output',(Join-Path $OutputDir 'counterfactual.json'))
        if ($Suite -eq 'All') {
            Invoke-EvaluationJob -Name 'audit' -Arguments @('scripts/audit_all.py','--app-root',$appRoot,'--out',(Join-Path $OutputDir 'audit'))
        }
    }
} catch {
    $jobs.Add([ordered]@{name='runner'; status=$_.Exception.Message; exit_code=1})
    Write-Warning $_.Exception.Message
} finally {
    if ($ownsBackend) {
        try {
            & $shellBinary -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'stop_web.ps1') -Port $Port
            $stopCode = $LASTEXITCODE
            $jobs.Add([ordered]@{name='owned-backend-cleanup'; status=$(if ($stopCode -eq 0) {'หยุดแล้ว'} else {'หยุดไม่สำเร็จ; ตรวจ launcher record'}); exit_code=$stopCode})
        } catch {
            $jobs.Add([ordered]@{name='owned-backend-cleanup'; status=$_.Exception.Message; exit_code=1})
        }
    }
    Save-EvaluationSummary
    Pop-Location
    # Copy only after every writer and owned backend has finished.
    $archiveCode = 1
    try {
        $ErrorActionPreference = 'Continue'
        & $pythonPath -X utf8 (Join-Path $PSScriptRoot 'archive_evaluation.py') archive --source $OutputDir --destination $EvidenceDir
        $archiveCode = $LASTEXITCODE
    } catch {
        Write-Warning $_.Exception.Message
    } finally { $ErrorActionPreference = 'Stop' }
    if ($archiveCode -eq 0) {
        Write-Host "Results: $EvidenceDir"
        Write-Host "Read: $(Join-Path $EvidenceDir 'REPORT.md')"
        Write-Host "Send: $(Join-Path $EvidenceDir 'evaluation-evidence.zip')"
    } else {
        $jobs.Add([ordered]@{name='evidence-archive'; status='เก็บหลักฐานในโครงการไม่สำเร็จ; ผลเดิมยังอยู่ใน working results'; exit_code=1})
        Save-EvaluationSummary
        Write-Warning "Evidence archive failed; working results are preserved: $OutputDir"
    }
    Write-Host "Working results: $OutputDir"
}
# Missing required coverage is incomplete, never a green full evaluation.
if (@($jobs | Where-Object { $null -eq $_.exit_code -or $_.exit_code -ne 0 }).Count -gt 0) { exit 1 }
exit 0
