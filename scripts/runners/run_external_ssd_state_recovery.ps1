# scripts/runners/run_external_ssd_state_recovery.ps1
#
# Purpose:
#   Compare an idle-start QD16 probe with a post-write QD16 probe while
#   preserving a fixed QD32 conditioning phase between them.
#
# Interpretation boundary:
#   This controls the externally visible sequence. It does not establish a
#   cold device state or prove an internal FTL/GC mechanism.

param(
    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_fio_testfile",

    [ValidateRange(1, 60)]
    [int]$InitialIdleMinutes = 5,

    [ValidateRange(0, 3600)]
    [int]$PostConditionIdleSec = 60,

    [switch]$ConfirmSamePort
)

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$ExperimentRoot = Join-Path $ResultRoot "_experiments"
$TracedRunner = Join-Path $BaseDir "scripts\runners\run_external_ssd_traced_sustained.ps1"

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = "state_write_recovery_001_$(Get-Date -Format 'yyyyMMdd')"
}

$SafeExperiment = $ExperimentLabel -replace '[^A-Za-z0-9_.-]', '_'
$ExperimentDir = Join-Path $ExperimentRoot $SafeExperiment
$ExperimentManifestPath = Join-Path $ExperimentDir "experiment_manifest.json"

$IdleStartRun = "sustained_${SafeExperiment}_idle_start_qd16_120s_repeat3"
$ConditionRun = "sustained_${SafeExperiment}_write_condition_qd32_300s_run1"
$PostWriteRun = "sustained_${SafeExperiment}_post_write_qd16_120s_repeat3"

if (-not $ConfirmSamePort) {
    throw "Re-run with -ConfirmSamePort after confirming the SSD remains on the same physical USB port."
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
    throw "Experiment manifest already exists. Use a new ExperimentLabel: $ExperimentManifestPath"
}

foreach ($runLabel in @($IdleStartRun, $ConditionRun, $PostWriteRun)) {
    $runDir = Join-Path $ResultRoot $runLabel
    if (Test-Path -LiteralPath $runDir) {
        $existingRuns = @(Get-ChildItem -LiteralPath $runDir -Filter "*_run*.json" -ErrorAction SilentlyContinue)
        if ($existingRuns.Count -gt 0) {
            throw "Result directory already contains fio JSON. Use a new ExperimentLabel: $runDir"
        }
    }
}

New-Item -ItemType Directory -Force $ExperimentDir | Out-Null

$Phases = @(
    [pscustomobject][ordered]@{
        order = 1
        state_phase = "idle_start_probe"
        test_case_id = "EXT-STATE-IDLE-START-PROBE"
        run_id = $IdleStartRun
        status = "planned"
        started_at = $null
        completed_at = $null
    },
    [pscustomobject][ordered]@{
        order = 2
        state_phase = "write_condition"
        test_case_id = "EXT-STATE-WRITE-CONDITION"
        run_id = $ConditionRun
        status = "planned"
        started_at = $null
        completed_at = $null
    },
    [pscustomobject][ordered]@{
        order = 3
        state_phase = "post_write_probe"
        test_case_id = "EXT-STATE-POST-WRITE-PROBE"
        run_id = $PostWriteRun
        status = "planned"
        started_at = $null
        completed_at = $null
    }
)

$Manifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeExperiment
    test_protocol_id = "EXT-STATE-WRITE-RECOVERY-001"
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_state_recovery.ps1"
    safety = "fio file target under E:\validation; no raw physical-drive writes"
    hypothesis = "A fixed preceding write workload may change subsequent QD16 throughput and tail latency."
    interpretation_boundary = "Idle-start and post-write are externally controlled labels, not proof of cold state, FTL behavior, or garbage collection."
    fixed_controls = [ordered]@{
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        test_file = $TestFile
        initial_idle_sec = $InitialIdleMinutes * 60
        post_condition_idle_sec = $PostConditionIdleSec
        probe = [ordered]@{ rw = "randwrite"; bs = "4k"; iodepth = 16; runtime_sec = 120; size = "512M"; repeats = 3; direct = 1 }
        conditioning = [ordered]@{ rw = "randwrite"; bs = "4k"; iodepth = 32; runtime_sec = 300; size = "512M"; repeats = 1; direct = 1 }
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
        [int]$Iodepth,
        [Parameter(Mandatory = $true)]
        [int]$Runs
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
        -Runs $Runs `
        -BlockSize 4k `
        -Size 512M `
        -TestFile $TestFile `
        -TestCaseId $Phase.test_case_id `
        -ExperimentId $SafeExperiment `
        -StatePhase $Phase.state_phase

    if ($LASTEXITCODE -ne 0) {
        throw "Phase $($Phase.state_phase) failed with exit code $LASTEXITCODE"
    }

    $Phase.status = "complete"
    $Phase.completed_at = (Get-Date).ToString("o")
    Save-ExperimentManifest
}

Save-ExperimentManifest

Write-Host "=== External SSD state-recovery experiment ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Test file  : $TestFile"
Write-Host "Sequence   : idle-start QD16 probe -> QD32 conditioning -> 60s idle -> post-write QD16 probe"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    $InitialIdleSec = $InitialIdleMinutes * 60
    Write-Host "[1/5] Initial idle interval: $InitialIdleSec seconds"
    Start-Sleep -Seconds $InitialIdleSec

    Write-Host "[2/5] Idle-start QD16 probe: 120s, repeat=3"
    Invoke-TracedPhase -Phase $Phases[0] -RuntimeSec 120 -Iodepth 16 -Runs 3

    Write-Host "[3/5] QD32 write conditioning: 300s, run=1"
    Invoke-TracedPhase -Phase $Phases[1] -RuntimeSec 300 -Iodepth 32 -Runs 1

    Write-Host "[4/5] Post-conditioning idle interval: $PostConditionIdleSec seconds"
    Start-Sleep -Seconds $PostConditionIdleSec

    Write-Host "[5/5] Post-write QD16 probe: 120s, repeat=3"
    Invoke-TracedPhase -Phase $Phases[2] -RuntimeSec 120 -Iodepth 16 -Runs 3

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

Write-Host "=== State-recovery experiment completed ==="
Write-Host "Experiment manifest: $ExperimentManifestPath"
Write-Host "Next: run the sustained analyzer and build one integrated manifest for each phase."
