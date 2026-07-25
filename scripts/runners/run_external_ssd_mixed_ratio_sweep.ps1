# scripts/runners/run_external_ssd_mixed_ratio_sweep.ps1
#
# Purpose:
#   Map mixed-workload response across 90:10, 70:30, and 50:50 read/write
#   ratios while counterbalancing sequence position across three cycles.

param(
    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_seq_32g",

    [ValidateSet("session1", "session2")]
    [string]$SequenceVariant = "session1",

    [ValidateRange(1, 1440)]
    [int]$ConfirmedDisconnectMinutes = 10,

    [ValidateRange(0, 60)]
    [int]$InitialIdleMinutes = 5,

    [ValidateRange(1, 86400)]
    [int]$RuntimeSec = 180,

    [ValidateRange(0, 3600)]
    [int]$InterPhaseIdleSec = 60,

    [ValidateRange(0, 7200)]
    [int]$InterCycleIdleSec = 300,

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
if ($SequenceVariant -eq "session2") {
    $ProtocolId = "EXT-MIXED-RATIO-SWEEP-REPRO-002"
    $DefaultLabel = "mixed_ratio_sweep_repro2_32g_$(Get-Date -Format 'yyyyMMdd')"
    $Question = "Does an independent counterbalanced session reproduce the ratio response and phase-transition pattern observed in session 1?"
    $HypothesisStatus = "independent_reproduction_of_descriptive_mapping"
} else {
    $ProtocolId = "EXT-MIXED-RATIO-SWEEP-001"
    $DefaultLabel = "mixed_ratio_sweep_32g_$(Get-Date -Format 'yyyyMMdd')"
    $Question = "How do read and write response metrics vary across 90:10, 70:30, and 50:50 mixes when each ratio occupies each sequence position once?"
    $HypothesisStatus = "exploratory_after_abba_baab_not_reproduced"
}

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = $DefaultLabel
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
    throw "fio command not found. Check PATH before starting the ratio sweep."
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
    $Value | ConvertTo-Json -Depth 10 | Out-File -FilePath $Path -Encoding utf8
}

if ($SequenceVariant -eq "session2") {
    $PhaseSpecs = @(
        [ordered]@{ order = 1; cycle = 1; position = 1; read_pct = 50 },
        [ordered]@{ order = 2; cycle = 1; position = 2; read_pct = 70 },
        [ordered]@{ order = 3; cycle = 1; position = 3; read_pct = 90 },
        [ordered]@{ order = 4; cycle = 2; position = 1; read_pct = 70 },
        [ordered]@{ order = 5; cycle = 2; position = 2; read_pct = 90 },
        [ordered]@{ order = 6; cycle = 2; position = 3; read_pct = 50 },
        [ordered]@{ order = 7; cycle = 3; position = 1; read_pct = 90 },
        [ordered]@{ order = 8; cycle = 3; position = 2; read_pct = 50 },
        [ordered]@{ order = 9; cycle = 3; position = 3; read_pct = 70 }
    )
} else {
    $PhaseSpecs = @(
        [ordered]@{ order = 1; cycle = 1; position = 1; read_pct = 90 },
        [ordered]@{ order = 2; cycle = 1; position = 2; read_pct = 70 },
        [ordered]@{ order = 3; cycle = 1; position = 3; read_pct = 50 },
        [ordered]@{ order = 4; cycle = 2; position = 1; read_pct = 70 },
        [ordered]@{ order = 5; cycle = 2; position = 2; read_pct = 50 },
        [ordered]@{ order = 6; cycle = 2; position = 3; read_pct = 90 },
        [ordered]@{ order = 7; cycle = 3; position = 1; read_pct = 50 },
        [ordered]@{ order = 8; cycle = 3; position = 2; read_pct = 90 },
        [ordered]@{ order = 9; cycle = 3; position = 3; read_pct = 70 }
    )
}

$CycleSequences = @()
foreach ($CycleNumber in 1..3) {
    $Sequence = @(
        $PhaseSpecs |
            Where-Object { $_.cycle -eq $CycleNumber } |
            Sort-Object position |
            ForEach-Object { "$($_.read_pct):$(100 - $_.read_pct)" }
    )
    $CycleSequences += [ordered]@{ cycle = $CycleNumber; sequence = $Sequence }
}

$Phases = @()
foreach ($Spec in $PhaseSpecs) {
    $WritePct = 100 - $Spec.read_pct
    $Phases += [pscustomobject][ordered]@{
        order = $Spec.order
        cycle = $Spec.cycle
        position = $Spec.position
        ratio = "$($Spec.read_pct):$WritePct"
        read_pct = $Spec.read_pct
        write_pct = $WritePct
        test_case_id = $ProtocolId
        workload = "mixed_$($Spec.read_pct)_$WritePct"
        status = "planned"
        started_at = $null
        completed_at = $null
        fio_json = $null
        log_prefix = $null
    }
}

$ReferenceExperiments = @(
    "mixed_read_qos_abba_32g_20260724",
    "mixed_read_qos_baab_32g_20260724"
)
if ($SequenceVariant -eq "session2") {
    $ReferenceExperiments += "mixed_ratio_sweep_32g_20260724"
}

$Manifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeExperiment
    test_protocol_id = $ProtocolId
    reference_experiments = $ReferenceExperiments
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_mixed_ratio_sweep.ps1"
    safety = "existing dedicated 32 GiB file target under E:\validation; no raw physical-drive target"
    question = $Question
    experimental_unit = "one three-phase cycle; three counterbalanced cycles form one descriptive mapping session"
    hypothesis_status = $HypothesisStatus
    interpretation_boundary = "Descriptive ratio-by-cycle-by-position mapping only; the design does not prove a causal device-internal interference mechanism."
    fixed_controls = [ordered]@{
        reconnect_start_confirmed = [bool]$ConfirmReconnectStart
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_file_write_confirmed = [bool]$ConfirmDedicatedFileWrite
        user_confirmed_disconnect_sec = $ConfirmedDisconnectMinutes * 60
        test_file = $TestFile
        observed_file_bytes = $TargetFile.Length
        sequence_variant = $SequenceVariant
        cycles = $CycleSequences
        block_size = "4k"
        iodepth = 16
        size = "32G"
        runtime_sec = $RuntimeSec
        time_based = $true
        direct = 1
        numjobs = 1
        ioengine = "windowsaio"
        randrepeat = 1
        initial_idle_sec = $InitialIdleMinutes * 60
        inter_phase_idle_sec = $InterPhaseIdleSec
        inter_cycle_idle_sec = $InterCycleIdleSec
    }
    analysis_plan = @(
        "report read and write bandwidth, IOPS, p99, p99.9, and maximum latency separately",
        "retain cycle and position beside every ratio result",
        "compare each ratio across all three positions before summarizing ratio response",
        "treat isolated maximum-latency events separately from percentile behavior",
        "do not claim internal cache, FTL, GC, NAND, firmware, or USB root cause"
    )
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
    runner = "scripts/runners/run_external_ssd_mixed_ratio_sweep.ps1"
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
    $env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "mixed_ratio_sweep_$SequenceVariant"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RW = "randrw_counterbalanced"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = $RuntimeSec.ToString()
    $env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "32G"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_BS = "4k"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "16"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = "9"
    $env:SSD_LAB_EXTERNAL_TEST_CASE_ID = $ProtocolId
    $env:SSD_LAB_EXTERNAL_EXPERIMENT_ID = $SafeExperiment
    $env:SSD_LAB_EXTERNAL_STATE_PHASE = "counterbalanced_ratio_sweep"

    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunLabel -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Observer $Phase failed with exit code $LASTEXITCODE"
    }
}

Save-ExperimentManifest
Save-RunnerManifest

Write-Host "=== External SSD counterbalanced mixed-ratio sweep ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Result set : $RunLabel"
Write-Host "Test file  : $TestFile"
Write-Host "Variant    : $SequenceVariant"
foreach ($Cycle in $CycleSequences) {
    Write-Host "Cycle $($Cycle.cycle)    : $($Cycle.sequence -join ' -> ')"
}
Write-Host "Runtime    : $RuntimeSec seconds per phase"
Write-Host "Start idle : $InitialIdleMinutes minutes"
Write-Host "Phase idle : $InterPhaseIdleSec seconds"
Write-Host "Cycle idle : $InterCycleIdleSec seconds"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    if ($InitialIdleMinutes -gt 0) {
        Write-Host "[idle] Waiting $InitialIdleMinutes minutes before cycle 1"
        Start-Sleep -Seconds ($InitialIdleMinutes * 60)
    }

    Write-Host "[observer] Collecting pre-sweep evidence"
    Invoke-Observer -Phase "pre"

    foreach ($Phase in $Phases) {
        $Order = $Phase.order
        $Cycle = $Phase.cycle
        $Position = $Phase.position
        $ReadPct = $Phase.read_pct
        $WritePct = $Phase.write_pct
        $RatioCode = "r${ReadPct}w${WritePct}"
        $OutFile = Join-Path $ResultDir "${RunLabel}_phase${Order}_c${Cycle}p${Position}_${RatioCode}.json"
        $LogPrefix = Join-Path $ResultDir "${RunLabel}_phase${Order}_c${Cycle}p${Position}_${RatioCode}"
        $RunRecord = [ordered]@{
            phase_order = $Order
            cycle = $Cycle
            position = $Position
            ratio = $Phase.ratio
            read_pct = $ReadPct
            write_pct = $WritePct
            started_at = (Get-Date).ToString("o")
            completed_at = $null
            status = "started"
            exit_code = $null
            fio_json = $OutFile
            log_prefix = $LogPrefix
        }

        $Phase.status = "running"
        $Phase.started_at = $RunRecord.started_at
        $Phase.fio_json = $OutFile
        $Phase.log_prefix = $LogPrefix
        Save-ExperimentManifest

        Write-Host "[phase $Order/9] cycle $Cycle position $Position - $($Phase.ratio)"
        $FioArgs = @(
            "--name=ratio_sweep_c${Cycle}p${Position}_${RatioCode}",
            "--filename=$TestFile",
            "--rw=randrw",
            "--rwmixread=$ReadPct",
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

        $RunRecord.completed_at = (Get-Date).ToString("o")
        $RunRecord.exit_code = $FioExitCode
        $RunRecord.status = if ($FioExitCode -eq 0) { "complete" } else { "failed" }
        $RunnerManifest.runs += $RunRecord
        Save-RunnerManifest

        if ($FioExitCode -ne 0) {
            throw "fio phase $Order failed with exit code $FioExitCode"
        }
        if (-not (Test-Path -LiteralPath $OutFile)) {
            throw "fio JSON was not created: $OutFile"
        }
        if (-not (Test-Path -LiteralPath $TestFile)) {
            throw "Dedicated target file is missing after phase ${Order}: $TestFile"
        }

        $Job = (Get-Content -Raw -LiteralPath $OutFile | ConvertFrom-Json).jobs[0]
        if ($Job.error -ne 0) {
            throw "fio JSON reports error=$($Job.error) for phase $Order"
        }
        if ($Job.read.io_bytes -le 0 -or $Job.write.io_bytes -le 0) {
            throw "Phase $Order did not record both read and write I/O."
        }

        $TotalBytes = $Job.read.io_bytes + $Job.write.io_bytes
        $ObservedReadShare = $Job.read.io_bytes / $TotalBytes
        $ExpectedReadShare = $ReadPct / 100.0
        if ([math]::Abs($ObservedReadShare - $ExpectedReadShare) -gt 0.01) {
            throw "Phase $Order did not preserve the expected $($Phase.ratio) mix."
        }

        $Phase.status = "complete"
        $Phase.completed_at = $RunRecord.completed_at
        Save-ExperimentManifest

        if ($Order -lt 9) {
            $IdleSec = if ($Position -eq 3) { $InterCycleIdleSec } else { $InterPhaseIdleSec }
            if ($IdleSec -gt 0) {
                $IdleKind = if ($Position -eq 3) { "cycle" } else { "phase" }
                Write-Host "[idle] Waiting $IdleSec seconds for the $IdleKind boundary"
                Start-Sleep -Seconds $IdleSec
            }
        }
    }

    $RunnerManifest.completed_at = (Get-Date).ToString("o")
    $RunnerManifest.status = "complete"
    Save-RunnerManifest

    Write-Host "[observer] Collecting post-sweep evidence"
    Invoke-Observer -Phase "post"

    $Manifest.completed_at = (Get-Date).ToString("o")
    $Manifest.status = "complete"
    Save-ExperimentManifest
}
catch {
    foreach ($Phase in $Phases) {
        if ($Phase.status -eq "running") {
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

Write-Host "=== Counterbalanced mixed-ratio sweep completed ==="
Write-Host "Expected fio JSON files: 9"
Write-Host "Actual fio JSON files  : $((Get-ChildItem -LiteralPath $ResultDir -Filter '*_phase*_c*p*_r*w*.json').Count)"
Write-Host "Result directory       : $ResultDir"
Write-Host "Runner manifest        : $RunnerManifestPath"
Write-Host "Experiment manifest    : $ExperimentManifestPath"
