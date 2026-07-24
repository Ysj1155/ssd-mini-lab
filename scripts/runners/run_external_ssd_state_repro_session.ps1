# scripts/runners/run_external_ssd_state_repro_session.ps1
#
# Purpose:
#   Execute one paired session for EXT-STATE-REPRO-002. The independent
#   experimental unit is the complete baseline-conditioning-post sequence,
#   not repeated fio probes inside one session.
#
# Interpretation boundary:
#   Reconnect-start is a user-confirmed external condition. It does not prove
#   that internal SSD state, NAND, cache, FTL, or garbage collection was reset.

param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 3)]
    [int]$SessionIndex,

    [string]$StudyId = "state_repro_002",
    [string]$SessionLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_fio_testfile",

    [ValidateRange(1, 1440)]
    [int]$ConfirmedDisconnectMinutes = 10,

    [ValidateRange(1, 60)]
    [int]$InitialIdleMinutes = 5,

    [ValidateRange(0, 3600)]
    [int]$PostConditionIdleSec = 60,

    [switch]$ConfirmReconnectStart,
    [switch]$ConfirmSamePort
)

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$ExperimentRoot = Join-Path $ResultRoot "_experiments"
$TracedRunner = Join-Path $BaseDir "scripts\runners\run_external_ssd_traced_sustained.ps1"

$SafeStudyId = $StudyId -replace '[^A-Za-z0-9_.-]', '_'
if ([string]::IsNullOrWhiteSpace($SessionLabel)) {
    $SessionLabel = "${SafeStudyId}_session${SessionIndex}_$(Get-Date -Format 'yyyyMMdd')"
}

$SafeSession = $SessionLabel -replace '[^A-Za-z0-9_.-]', '_'
$ExperimentDir = Join-Path $ExperimentRoot $SafeSession
$ExperimentManifestPath = Join-Path $ExperimentDir "experiment_manifest.json"

$BaselineRun = "sustained_${SafeSession}_baseline_qd16_120s_run1"
$ConditionRun = "sustained_${SafeSession}_condition_qd32_300s_run1"
$PostRun = "sustained_${SafeSession}_post_qd16_120s_run1"

if (-not $ConfirmReconnectStart) {
    throw "Re-run with -ConfirmReconnectStart after safely reconnecting the SSD for this session."
}
if (-not $ConfirmSamePort) {
    throw "Re-run with -ConfirmSamePort after confirming the same physical USB port."
}
if (-not ($TestFile -like "E:\validation\*")) {
    throw "TestFile must stay under E:\validation. Current: $TestFile"
}
if (-not (Test-Path -LiteralPath $TestFile)) {
    throw "Test file does not exist: $TestFile"
}
if (-not (Test-Path -LiteralPath $TracedRunner)) {
    throw "Traced runner not found: $TracedRunner"
}
if ($null -eq (Get-Command fio -ErrorAction SilentlyContinue)) {
    throw "fio command not found. Check PATH before starting the idle interval."
}
if (Test-Path -LiteralPath $ExperimentManifestPath) {
    throw "Session manifest already exists. Use a new SessionLabel: $ExperimentManifestPath"
}

foreach ($runLabel in @($BaselineRun, $ConditionRun, $PostRun)) {
    $runDir = Join-Path $ResultRoot $runLabel
    if (Test-Path -LiteralPath $runDir) {
        $existingRuns = @(Get-ChildItem -LiteralPath $runDir -Filter "*_run*.json" -ErrorAction SilentlyContinue)
        if ($existingRuns.Count -gt 0) {
            throw "Result directory already contains fio JSON. Use a new SessionLabel: $runDir"
        }
    }
}

New-Item -ItemType Directory -Force $ExperimentDir | Out-Null

$Phases = @(
    [pscustomobject][ordered]@{
        order = 1
        state_phase = "session_baseline_probe"
        test_case_id = "EXT-STATE-REPRO-BASELINE"
        run_id = $BaselineRun
        status = "planned"
        started_at = $null
        completed_at = $null
    },
    [pscustomobject][ordered]@{
        order = 2
        state_phase = "session_write_condition"
        test_case_id = "EXT-STATE-REPRO-CONDITION"
        run_id = $ConditionRun
        status = "planned"
        started_at = $null
        completed_at = $null
    },
    [pscustomobject][ordered]@{
        order = 3
        state_phase = "session_post_write_probe"
        test_case_id = "EXT-STATE-REPRO-POST"
        run_id = $PostRun
        status = "planned"
        started_at = $null
        completed_at = $null
    }
)

$Manifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeSession
    study_id = $SafeStudyId
    session_index = $SessionIndex
    test_protocol_id = "EXT-STATE-REPRO-002"
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_state_repro_session.ps1"
    safety = "fio file target under E:\validation; no raw physical-drive writes"
    hypothesis = "The direction of the QD16 post-write delta may reproduce across independently initiated paired sessions."
    experimental_unit = "one complete reconnect-start baseline-conditioning-post session"
    interpretation_boundary = "Reconnect-start is externally controlled but is not proof of an internally reset or cold SSD state."
    fixed_controls = [ordered]@{
        reconnect_start_confirmed = [bool]$ConfirmReconnectStart
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        user_confirmed_disconnect_sec = $ConfirmedDisconnectMinutes * 60
        test_file = $TestFile
        initial_idle_sec = $InitialIdleMinutes * 60
        post_condition_idle_sec = $PostConditionIdleSec
        baseline_probe = [ordered]@{ rw = "randwrite"; bs = "4k"; iodepth = 16; runtime_sec = 120; size = "512M"; repeats = 1; direct = 1 }
        conditioning = [ordered]@{ rw = "randwrite"; bs = "4k"; iodepth = 32; runtime_sec = 300; size = "512M"; repeats = 1; direct = 1 }
        post_write_probe = [ordered]@{ rw = "randwrite"; bs = "4k"; iodepth = 16; runtime_sec = 120; size = "512M"; repeats = 1; direct = 1 }
    }
    phases = $Phases
    error = $null
}

function Save-ExperimentManifest {
    $Manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $ExperimentManifestPath -Encoding utf8
}

function Invoke-TracedPhase {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Phase,
        [Parameter(Mandatory = $true)]
        [int]$RuntimeSec,
        [Parameter(Mandatory = $true)]
        [int]$Iodepth
    )

    $Phase.status = "running"
    $Phase.started_at = (Get-Date).ToString("o")
    Save-ExperimentManifest

    powershell -ExecutionPolicy Bypass `
        -File $TracedRunner `
        -RunLabel $Phase.run_id `
        -Rw randwrite `
        -RuntimeSec $RuntimeSec `
        -Iodepth $Iodepth `
        -Runs 1 `
        -BlockSize 4k `
        -Size 512M `
        -TestFile $TestFile `
        -TestCaseId $Phase.test_case_id `
        -ExperimentId $SafeSession `
        -StatePhase $Phase.state_phase

    if ($LASTEXITCODE -ne 0) {
        throw "Phase $($Phase.state_phase) failed with exit code $LASTEXITCODE"
    }

    $Phase.status = "complete"
    $Phase.completed_at = (Get-Date).ToString("o")
    Save-ExperimentManifest
}

Save-ExperimentManifest

Write-Host "=== External SSD state reproducibility session ==="
Write-Host "Study       : $SafeStudyId"
Write-Host "Session     : $SessionIndex / 3"
Write-Host "Session ID  : $SafeSession"
Write-Host "Test file   : $TestFile"
Write-Host "Sequence    : baseline QD16 run1 -> QD32 condition run1 -> 60s idle -> post QD16 run1"
Write-Host "Manifest    : $ExperimentManifestPath"
Write-Host ""

try {
    $InitialIdleSec = $InitialIdleMinutes * 60
    Write-Host "[1/5] Reconnect-start idle interval: $InitialIdleSec seconds"
    Start-Sleep -Seconds $InitialIdleSec

    Write-Host "[2/5] Session baseline QD16 probe: 120s, run=1"
    Invoke-TracedPhase -Phase $Phases[0] -RuntimeSec 120 -Iodepth 16

    Write-Host "[3/5] QD32 write conditioning: 300s, run=1"
    Invoke-TracedPhase -Phase $Phases[1] -RuntimeSec 300 -Iodepth 32

    Write-Host "[4/5] Post-conditioning idle interval: $PostConditionIdleSec seconds"
    Start-Sleep -Seconds $PostConditionIdleSec

    Write-Host "[5/5] Session post-write QD16 probe: 120s, run=1"
    Invoke-TracedPhase -Phase $Phases[2] -RuntimeSec 120 -Iodepth 16

    $Manifest.completed_at = (Get-Date).ToString("o")
    $Manifest.status = "complete"
    Save-ExperimentManifest
}
catch {
    foreach ($phase in $Phases) {
        if ($phase.status -eq "running") {
            $phase.status = "failed"
            $phase.completed_at = (Get-Date).ToString("o")
        }
    }
    $Manifest.completed_at = (Get-Date).ToString("o")
    $Manifest.status = "failed"
    $Manifest.error = $_.Exception.Message
    Save-ExperimentManifest
    throw
}

Write-Host "=== State reproducibility session completed ==="
Write-Host "Session manifest: $ExperimentManifestPath"
Write-Host "Keep this session unchanged and repeat the same protocol with the next SessionIndex."
