# scripts/observers/collect_external_ssd_observer.ps1
#
# Purpose:
#   Collect external SSD validation observer evidence without running fio.
#
# Output:
#   results/external_ssd/<run_id>/observer_manifest_<phase>.json
#
# Safety:
#   This script does not run fio.
#   This script does not write to raw block devices.
#   It only calls read-only environment and telemetry collectors.

param(
    [string]$RunLabel = $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL,
    [string]$Phase = $env:SSD_LAB_OBSERVER_PHASE,
    [switch]$SkipEnvironment,
    [switch]$SkipTelemetry
)

$ErrorActionPreference = "Continue"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\external_ssd"

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
        limitation = $null
    }

    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        $record.completed_at = (Get-Date).ToString("o")
        $record.exit_code = 1
        $record.status = "limited"
        $record.limitation = "collector script not found"
        return $record
    }

    powershell -ExecutionPolicy Bypass -File $ScriptPath
    $record.exit_code = $LASTEXITCODE
    $record.completed_at = (Get-Date).ToString("o")

    $manifest = Read-CollectorManifest -Path $LatestManifestPath
    if ($null -ne $manifest) {
        $record.output_dir = $manifest.output_dir
    }

    if ($LASTEXITCODE -eq 0 -and $null -ne $manifest) {
        $record.status = "complete"
    }
    else {
        $record.status = "limited"
        $record.limitation = "collector did not return a usable manifest"
    }

    return $record
}

$collectors = @()
$limitations = @()

if (-not $SkipEnvironment) {
    $collectors += Invoke-Collector `
        -Name "environment" `
        -ScriptPath (Join-Path $BaseDir "scripts\collect_env_windows.ps1") `
        -LatestManifestPath (Join-Path $BaseDir "results\env\latest\manifest.json")
}
else {
    $limitations += "environment collector skipped"
}

if (-not $SkipTelemetry) {
    $collectors += Invoke-Collector `
        -Name "storage_telemetry" `
        -ScriptPath (Join-Path $BaseDir "scripts\collect_storage_telemetry_windows.ps1") `
        -LatestManifestPath (Join-Path $BaseDir "results\telemetry\latest\manifest.json")
}
else {
    $limitations += "storage telemetry collector skipped"
}

foreach ($collector in $collectors) {
    if ($collector.status -ne "complete") {
        $limitations += "$($collector.name): $($collector.limitation)"
    }
}

$Status = if ($limitations.Count -eq 0) { "complete" } else { "limited" }

$ObserverManifest = [ordered]@{
    schema_version = "1.0"
    role = "observer"
    run_id = $SafeLabel
    phase = $SafePhase
    collected_at = (Get-Date).ToString("o")
    status = $Status
    observer = "scripts/observers/collect_external_ssd_observer.ps1"
    safety = "read-only observer; no fio execution; no raw physical-drive writes"
    collectors = $collectors
    limitations = $limitations
}

$ObserverManifest |
    ConvertTo-Json -Depth 8 |
    Out-File -FilePath $ObserverManifestPath -Encoding utf8

Write-Host "=== External SSD observer evidence collected ==="
Write-Host "Run ID   : $SafeLabel"
Write-Host "Phase    : $SafePhase"
Write-Host "Status   : $Status"
Write-Host "Manifest : $ObserverManifestPath"