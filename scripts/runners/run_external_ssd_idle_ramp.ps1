# scripts/runners/run_external_ssd_idle_ramp.ps1
#
# Purpose:
#   Test whether requested pre-probe idle duration is associated with the
#   presence or timing of the phase-start bandwidth ramp under one fixed
#   70:30 random workload.

param(
    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_seq_32g",

    [ValidateRange(1, 1440)]
    [int]$ConfirmedDisconnectMinutes = 10,

    [ValidateRange(60, 600)]
    [int]$RuntimeSec = 120,

    [switch]$ConfirmReconnectStart,
    [switch]$ConfirmSamePort,
    [switch]$ConfirmDedicatedFileWrite
)

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$ExperimentRoot = Join-Path $ResultRoot "_experiments"
$ObserverScript = Join-Path $BaseDir "scripts\observers\collect_external_ssd_observer.ps1"
$ExpectedBytes = 32GB
$ProtocolId = "EXT-IDLE-RAMP-001"

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = "idle_ramp_7030_32g_$(Get-Date -Format 'yyyyMMdd')"
}

$SafeExperiment = $ExperimentLabel -replace '[^A-Za-z0-9_.-]', '_'
$RunLabel = "sustained_${SafeExperiment}"
$ResultDir = Join-Path $ResultRoot $RunLabel
$RunnerManifestPath = Join-Path $ResultDir "runner_manifest.json"
$ExperimentDir = Join-Path $ExperimentRoot $SafeExperiment
$ExperimentManifestPath = Join-Path $ExperimentDir "experiment_manifest.json"

if (-not $ConfirmReconnectStart) {
    throw "Re-run with -ConfirmReconnectStart after a safe disconnect and reconnect."
}
if (-not $ConfirmSamePort) {
    throw "Re-run with -ConfirmSamePort after confirming the same physical USB port."
}
if (-not $ConfirmDedicatedFileWrite) {
    throw "Re-run with -ConfirmDedicatedFileWrite after confirming writes target the dedicated file."
}
if (-not ($TestFile -like "E:\validation\*")) {
    throw "TestFile must stay under E:\validation. Current: $TestFile"
}
if (-not (Test-Path -LiteralPath $TestFile)) {
    throw "Dedicated 32 GiB test file does not exist: $TestFile"
}
if (-not (Test-Path -LiteralPath $ObserverScript)) {
    throw "Observer script not found: $ObserverScript"
}
if ($null -eq (Get-Command fio -ErrorAction SilentlyContinue)) {
    throw "fio command not found. Check PATH before starting the idle-ramp experiment."
}
if (Test-Path -LiteralPath $ExperimentManifestPath) {
    throw "Experiment manifest already exists. Use a new ExperimentLabel: $ExperimentManifestPath"
}
if (Test-Path -LiteralPath $ResultDir) {
    $ExistingJson = @(Get-ChildItem -LiteralPath $ResultDir -Filter "*.json" -ErrorAction SilentlyContinue)
    if ($ExistingJson.Count -gt 0) {
        throw "Result directory already contains JSON. Use a new ExperimentLabel: $ResultDir"
    }
}

$TargetFile = Get-Item -LiteralPath $TestFile -ErrorAction Stop
if ($TargetFile.Length -ne $ExpectedBytes) {
    throw "Test file must be exactly 32 GiB. Expected=$ExpectedBytes, actual=$($TargetFile.Length)"
}

New-Item -ItemType Directory -Force $ExperimentDir | Out-Null
New-Item -ItemType Directory -Force $ResultDir | Out-Null

function Save-Json {
    param([object]$Value, [string]$Path)
    $Value | ConvertTo-Json -Depth 12 | Out-File -FilePath $Path -Encoding utf8
}

# A-B-C-C-B-A mirrors each idle condition across early and late positions.
$PhaseSpecs = @(
    [ordered]@{ order = 1; code = "A1"; idle_sec = 300; replicate = 1 },
    [ordered]@{ order = 2; code = "B1"; idle_sec = 60; replicate = 1 },
    [ordered]@{ order = 3; code = "C1"; idle_sec = 0; replicate = 1 },
    [ordered]@{ order = 4; code = "C2"; idle_sec = 0; replicate = 2 },
    [ordered]@{ order = 5; code = "B2"; idle_sec = 60; replicate = 2 },
    [ordered]@{ order = 6; code = "A2"; idle_sec = 300; replicate = 2 }
)

$Phases = @()
foreach ($Spec in $PhaseSpecs) {
    $Phases += [pscustomobject][ordered]@{
        order = $Spec.order
        code = $Spec.code
        requested_pre_probe_idle_sec = $Spec.idle_sec
        condition_replicate = $Spec.replicate
        test_case_id = $ProtocolId
        workload = "randrw_70_30"
        status = "planned"
        idle_started_at = $null
        fio_started_at = $null
        completed_at = $null
        actual_controlled_idle_sec = $null
        previous_fio_gap_sec = $null
        fio_json = $null
        log_prefix = $null
    }
}

$Manifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeExperiment
    test_protocol_id = $ProtocolId
    reference_experiments = @(
        "mixed_ratio_sweep_32g_20260724",
        "mixed_ratio_sweep_repro2_32g_20260724"
    )
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_idle_ramp.ps1"
    safety = "existing dedicated 32 GiB file target under E:\validation; no raw physical-drive target"
    question = "Does requested pre-probe idle duration change phase-start ramp presence or transition time under a fixed 70:30 random workload?"
    experimental_unit = "one 120-second 70:30 probe preceded by a requested intentional idle interval"
    primary_metric = "transition_sec: first five consecutive 1-second total-bandwidth samples at or above 80% of the last-third mean"
    interpretation_boundary = "Idle duration is an externally controlled interval. Association does not identify USB, host power, OS, filesystem, firmware, cache, FTL, GC, NAND, or thermal root cause."
    fixed_controls = [ordered]@{
        reconnect_start_confirmed = [bool]$ConfirmReconnectStart
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_file_write_confirmed = [bool]$ConfirmDedicatedFileWrite
        user_confirmed_disconnect_sec = $ConfirmedDisconnectMinutes * 60
        test_file = $TestFile
        observed_file_bytes = $TargetFile.Length
        sequence_design = "A-B-C-C-B-A"
        requested_pre_probe_idle_sequence_sec = @(300, 60, 0, 0, 60, 300)
        zero_idle_definition = "no intentional Start-Sleep; actual gap includes runner bookkeeping"
        rw = "randrw"
        rwmixread = 70
        rwmixwrite = 30
        block_size = "4k"
        iodepth = 16
        size = "32G"
        runtime_sec = $RuntimeSec
        time_based = $true
        direct = 1
        numjobs = 1
        ioengine = "windowsaio"
        randrepeat = 1
    }
    analysis_plan = [ordered]@{
        transition_plateau_window = "last_third"
        transition_plateau_fraction = 0.80
        transition_consecutive_samples = 5
        ramp_present_rule = "transition_sec >= 10 and plateau_over_first_third >= 1.30"
        pair_consistency_rule = "same ramp_present value and, when present, transition-time range <= 20 seconds"
        association_rule = "all three idle pairs consistent and ramp frequency or transition time increases with idle duration"
        compare_by = @(
            "requested_pre_probe_idle_sec",
            "condition_replicate",
            "sequence_position"
        )
    }
    phases = $Phases
    error = $null
}

$RunnerManifest = [ordered]@{
    schema_version = "1.0"
    role = "runner"
    run_id = $RunLabel
    test_case_id = $ProtocolId
    experiment_id = $SafeExperiment
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    runner = "scripts/runners/run_external_ssd_idle_ramp.ps1"
    safety = "time-based fio file-target runner; no raw physical-drive target"
    result_dir = $ResultDir
    test_file = $TestFile
    conditions = $Manifest.fixed_controls
    runs = @()
}

function Save-ExperimentManifest {
    Save-Json -Value $Manifest -Path $ExperimentManifestPath
}

function Save-RunnerManifest {
    Save-Json -Value $RunnerManifest -Path $RunnerManifestPath
}

function Invoke-Observer {
    param([string]$Phase)

    $env:SSD_LAB_EXTERNAL_TESTFILE = $TestFile
    $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL = $RunLabel
    $env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "idle_ramp_7030"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RW = "randrw"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = $RuntimeSec.ToString()
    $env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "32G"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_BS = "4k"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "16"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = "6"
    $env:SSD_LAB_EXTERNAL_TEST_CASE_ID = $ProtocolId
    $env:SSD_LAB_EXTERNAL_EXPERIMENT_ID = $SafeExperiment
    $env:SSD_LAB_EXTERNAL_STATE_PHASE = "idle_ramp_symmetric_sequence"

    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunLabel -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Observer $Phase failed with exit code $LASTEXITCODE"
    }
}

Save-ExperimentManifest
Save-RunnerManifest

Write-Host "=== External SSD idle-ramp experiment ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Result set : $RunLabel"
Write-Host "Test file  : $TestFile"
Write-Host "Sequence   : 300s -> 60s -> 0s -> 0s -> 60s -> 300s"
Write-Host "Workload   : randrw 70:30, 4K, QD16, 32G, $RuntimeSec seconds"
Write-Host "Metric     : first 5s >= 80% of last-third mean total BW"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

$PreviousFioCompletedAt = $null

try {
    Write-Host "[observer] Collecting pre-sequence evidence before controlled idle"
    Invoke-Observer -Phase "pre"

    foreach ($Phase in $Phases) {
        $Order = $Phase.order
        $Code = $Phase.code
        $IdleSec = $Phase.requested_pre_probe_idle_sec
        $IdleCode = "idle${IdleSec}"
        $OutFile = Join-Path $ResultDir "${RunLabel}_phase${Order}_${Code}_${IdleCode}.json"
        $LogPrefix = Join-Path $ResultDir "${RunLabel}_phase${Order}_${Code}_${IdleCode}"
        $IdleStartedAt = Get-Date

        $Phase.status = "idle"
        $Phase.idle_started_at = $IdleStartedAt.ToString("o")
        $Phase.fio_json = $OutFile
        $Phase.log_prefix = $LogPrefix
        Save-ExperimentManifest

        if ($IdleSec -gt 0) {
            Write-Host "[phase $Order/6] $Code - waiting $IdleSec seconds before fio"
            Start-Sleep -Seconds $IdleSec
        } else {
            Write-Host "[phase $Order/6] $Code - no intentional pre-probe sleep"
        }

        $FioStartedAt = Get-Date
        $ActualControlledIdleSec = ($FioStartedAt - $IdleStartedAt).TotalSeconds
        $PreviousGapSec = if ($null -eq $PreviousFioCompletedAt) {
            $null
        } else {
            ($FioStartedAt - $PreviousFioCompletedAt).TotalSeconds
        }

        $RunRecord = [ordered]@{
            phase_order = $Order
            phase_code = $Code
            requested_pre_probe_idle_sec = $IdleSec
            condition_replicate = $Phase.condition_replicate
            idle_started_at = $IdleStartedAt.ToString("o")
            fio_started_at = $FioStartedAt.ToString("o")
            completed_at = $null
            actual_controlled_idle_sec = $ActualControlledIdleSec
            previous_fio_gap_sec = $PreviousGapSec
            status = "started"
            exit_code = $null
            ratio = "70:30"
            read_pct = 70
            write_pct = 30
            fio_json = $OutFile
            log_prefix = $LogPrefix
        }

        $Phase.status = "running"
        $Phase.fio_started_at = $RunRecord.fio_started_at
        $Phase.actual_controlled_idle_sec = $ActualControlledIdleSec
        $Phase.previous_fio_gap_sec = $PreviousGapSec
        Save-ExperimentManifest

        $FioArgs = @(
            "--name=idle_ramp_${Code}_${IdleCode}",
            "--filename=$TestFile",
            "--rw=randrw",
            "--rwmixread=70",
            "--bs=4k",
            "--iodepth=16",
            "--size=32G",
            "--runtime=$RuntimeSec",
            "--time_based=1",
            "--direct=1",
            "--ioengine=windowsaio",
            "--numjobs=1",
            "--thread=1",
            "--randrepeat=1",
            "--overwrite=1",
            "--group_reporting=1",
            "--log_avg_msec=1000",
            "--write_bw_log=$LogPrefix",
            "--write_iops_log=$LogPrefix",
            "--write_lat_log=$LogPrefix",
            "--output-format=json",
            "--output=$OutFile"
        )

        & fio @FioArgs
        $FioExitCode = $LASTEXITCODE
        $PreviousFioCompletedAt = Get-Date

        $RunRecord.completed_at = $PreviousFioCompletedAt.ToString("o")
        $RunRecord.exit_code = $FioExitCode
        $RunRecord.status = if ($FioExitCode -eq 0) { "complete" } else { "failed" }
        $RunnerManifest.runs += $RunRecord
        Save-RunnerManifest

        if ($FioExitCode -ne 0) {
            throw "fio phase $Code failed with exit code $FioExitCode"
        }
        if (-not (Test-Path -LiteralPath $OutFile)) {
            throw "fio JSON was not created: $OutFile"
        }
        if (-not (Test-Path -LiteralPath $TestFile)) {
            throw "Dedicated target file is missing after phase ${Code}: $TestFile"
        }

        $Job = (Get-Content -Raw -LiteralPath $OutFile | ConvertFrom-Json).jobs[0]
        if ($Job.error -ne 0) {
            throw "fio JSON reports error=$($Job.error) for phase $Code"
        }
        if ($Job.read.io_bytes -le 0 -or $Job.write.io_bytes -le 0) {
            throw "Phase $Code did not record both read and write I/O."
        }
        $TotalBytes = $Job.read.io_bytes + $Job.write.io_bytes
        $ObservedReadShare = $Job.read.io_bytes / $TotalBytes
        if ([math]::Abs($ObservedReadShare - 0.70) -gt 0.01) {
            throw "Phase $Code did not preserve the expected 70:30 mix."
        }

        $Phase.status = "complete"
        $Phase.completed_at = $RunRecord.completed_at
        Save-ExperimentManifest
    }

    $RunnerManifest.completed_at = (Get-Date).ToString("o")
    $RunnerManifest.status = "complete"
    Save-RunnerManifest

    Write-Host "[observer] Collecting post-sequence evidence"
    Invoke-Observer -Phase "post"

    $Manifest.completed_at = (Get-Date).ToString("o")
    $Manifest.status = "complete"
    Save-ExperimentManifest
}
catch {
    foreach ($Phase in $Phases) {
        if ($Phase.status -in @("idle", "running")) {
            $Phase.status = "failed"
            $Phase.completed_at = (Get-Date).ToString("o")
        }
    }
    $RunnerManifest.completed_at = (Get-Date).ToString("o")
    $RunnerManifest.status = "failed"
    Save-RunnerManifest
    $Manifest.completed_at = (Get-Date).ToString("o")
    $Manifest.status = "failed"
    $Manifest.error = $_.Exception.Message
    Save-ExperimentManifest
    throw
}

Write-Host "=== External SSD idle-ramp experiment completed ==="
Write-Host "Expected fio JSON files: 6"
Write-Host "Actual fio JSON files  : $((Get-ChildItem -LiteralPath $ResultDir -Filter '*_phase*_idle*.json').Count)"
Write-Host "Result directory       : $ResultDir"
Write-Host "Runner manifest        : $RunnerManifestPath"
Write-Host "Experiment manifest    : $ExperimentManifestPath"
