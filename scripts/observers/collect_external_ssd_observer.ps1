# scripts/observers/collect_external_ssd_observer.ps1
#
# Purpose:
#   Collect external SSD validation observer evidence without running fio.
#
# Output:
#   results/external_ssd/<run_id>/observer_manifest_<phase>.json

param(
    [string]$RunLabel = $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL,
    [string]$Phase = $env:SSD_LAB_OBSERVER_PHASE,
    [switch]$SkipEnvironment,
    [switch]$SkipTelemetry
)

$ErrorActionPreference = "Continue"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$TestFile = $env:SSD_LAB_EXTERNAL_TESTFILE

if ([string]::IsNullOrWhiteSpace($RunLabel)) {
    $RunLabel = "external_ssd_observer_unlabeled"
}

if ([string]::IsNullOrWhiteSpace($Phase)) {
    $Phase = "pre"
}

$SafeLabel = $RunLabel -replace '[^A-Za-z0-9_.-]', '_'
$SafePhase = $Phase -replace '[^A-Za-z0-9_.-]', '_'
$ResultDir = Join-Path $ResultRoot $SafeLabel
$ObserverManifestPath = Join-Path $ResultDir "observer_manifest_${SafePhase}.json"

New-Item -ItemType Directory -Force $ResultDir | Out-Null

function Read-CollectorManifest {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    try {
        return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Invoke-Collector {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string]$LatestManifestPath
    )

    $record = [ordered]@{
        name = $Name
        collector = $ScriptPath
        started_at = (Get-Date).ToString("o")
        completed_at = $null
        exit_code = $null
        status = "started"
        latest_manifest = $LatestManifestPath
        output_dir = $null
        target_file = $null
        limitations = @()
        limitation = $null
    }

    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        $record.completed_at = (Get-Date).ToString("o")
        $record.exit_code = 1
        $record.status = "limited"
        $record.limitations = @("collector script not found")
        $record.limitation = "collector script not found"
        return $record
    }

    powershell -ExecutionPolicy Bypass -File $ScriptPath | Out-Host
    $collectorExitCode = $LASTEXITCODE
    $record.exit_code = $collectorExitCode
    $record.completed_at = (Get-Date).ToString("o")

    $manifest = Read-CollectorManifest -Path $LatestManifestPath
    if ($null -ne $manifest) {
        $record.output_dir = $manifest.output_dir
        $record.target_file = $manifest.target_file
        if ($null -ne $manifest.limitations) {
            $record.limitations = @($manifest.limitations)
        }
    }

    if ($collectorExitCode -ne 0 -or $null -eq $manifest) {
        $record.status = "limited"
        $record.limitations += "collector did not return a usable manifest"
    }
    elseif ($manifest.PSObject.Properties.Name -contains "status") {
        $record.status = $manifest.status
    }
    else {
        $record.status = "complete"
    }

    if ($record.limitations.Count -gt 0) {
        $record.limitation = $record.limitations -join "; "
    }

    return $record
}

$Collectors = @()
$Limitations = @()

if (-not $SkipEnvironment) {
    $Collectors += Invoke-Collector `
        -Name "environment" `
        -ScriptPath (Join-Path $BaseDir "scripts\collect_env_windows.ps1") `
        -LatestManifestPath (Join-Path $BaseDir "results\env\latest\manifest.json")
}
else {
    $Limitations += "environment collector skipped"
}

if (-not $SkipTelemetry) {
    $Collectors += Invoke-Collector `
        -Name "storage_telemetry" `
        -ScriptPath (Join-Path $BaseDir "scripts\collect_storage_telemetry_windows.ps1") `
        -LatestManifestPath (Join-Path $BaseDir "results\telemetry\latest\manifest.json")
}
else {
    $Limitations += "storage telemetry collector skipped"
}

foreach ($collector in $Collectors) {
    if ($collector.status -ne "complete") {
        $detail = if ($collector.limitation) { $collector.limitation } else { $collector.status }
        $Limitations += "$($collector.name): $detail"
    }
}

$Status = if ($Limitations.Count -eq 0) { "complete" } else { "limited" }

$ObserverManifest = [ordered]@{
    schema_version = "1.0"
    role = "observer"
    run_id = $SafeLabel
    phase = $SafePhase
    collected_at = (Get-Date).ToString("o")
    status = $Status
    observer = "scripts/observers/collect_external_ssd_observer.ps1"
    target_file = $TestFile
    safety = "read-only observer; no fio execution; no raw physical-drive writes"
    collectors = $Collectors
    limitations = $Limitations
}

$ObserverManifest |
    ConvertTo-Json -Depth 8 |
    Out-File -FilePath $ObserverManifestPath -Encoding utf8

Write-Host "=== External SSD observer evidence collected ==="
Write-Host "Run ID   : $SafeLabel"
Write-Host "Phase    : $SafePhase"
Write-Host "Status   : $Status"
Write-Host "Manifest : $ObserverManifestPath"
