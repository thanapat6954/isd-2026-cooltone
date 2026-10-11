# Find an executable for this process; do not change the user's persisted PATH.
function Resolve-EvaluationNode {
    param([string]$NodePath = '')
    $candidates = [Collections.Generic.List[string]]::new()
    if ($NodePath) {
        if (-not (Test-Path -LiteralPath $NodePath -PathType Leaf)) { throw "NodePath does not exist: $NodePath" }
        $candidates.Add([IO.Path]::GetFullPath($NodePath))
    } else {
        $command = Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) { $candidates.Add($command.Source) }
        # VS Code may have inherited PATH before an installation or runtime setup.
        foreach ($scope in @('Machine','User')) {
            foreach ($folder in ([Environment]::GetEnvironmentVariable('Path',$scope) -split ';')) {
                if ($folder.Trim()) {
                    $expanded = [Environment]::ExpandEnvironmentVariables($folder.Trim().Trim('"'))
                    $candidates.Add((Join-Path $expanded 'node.exe'))
                }
            }
        }
        foreach ($folder in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
            if ($folder) { $candidates.Add((Join-Path $folder 'nodejs/node.exe')) }
        }
        if ($env:USERPROFILE) {
            $candidates.Add((Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'))
        }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $version = & $candidate --version
        if ($LASTEXITCODE -eq 0 -and "$version" -match '^v(\d+)\.' -and [int]$Matches[1] -ge 18) {
            $resolved = [IO.Path]::GetFullPath($candidate)
            $env:PATH = (Split-Path $resolved -Parent) + [IO.Path]::PathSeparator + $env:PATH
            Write-Host "Node.js $version : $resolved"
            return $resolved
        }
    }
    throw 'Node.js 18+ was not found. Install Node.js or pass -NodePath with the full path to node.exe.'
}
