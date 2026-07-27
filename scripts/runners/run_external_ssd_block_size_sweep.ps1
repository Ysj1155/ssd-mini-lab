# scripts/runners/run_external_ssd_block_size_sweep.ps1
#
# Purpose:
#   Map 4K, 64K, and 1M random-I/O response while counterbalancing each
#   block size across sequence position. Read and write run as independent
#   reconnect-start sessions.

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("randread", "randwrite")]
    [string]$Workload,

    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_seq_32g",

    [ValidateRange(1, 1440)]
    [int]$ConfirmedDisconnectMinutes = 10,

    [ValidateRange(0, 60)]
    [int]$InitialIdleMinutes = 5,

    [ValidateRange(10, 600)]
    [int]$RuntimeSec = 30,

    [ValidateRange(0, 3600)]
    [int]$InterPhaseIdleSec = 60,

    [switch]$ConfirmReconnectStart,
    [switch]$ConfirmSamePort,
    [switch]$ConfirmDedicatedFileWrite
)

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$SafetyModule = Join-Path $BaseDir "scripts\lib\ExternalSsdSafety.psm1"
$DutIdentityConfig = Join-Path $BaseDir "configs\external_ssd_dut_identity.json"
Import-Module $SafetyModule -Force
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$ExperimentRoot = Join-Path $ResultRoot "_experiments"
$ObserverScript = Join-Path $BaseDir "scripts\observers\collect_external_ssd_observer.ps1"
$ExpectedBytes = 32GB

if ($Workload -eq "randread") {
    $ProtocolId = "EXT-BS-RANDREAD-001"
    $DefaultLabel = "block_size_randread_32g_$(Get-Date -Format 'yyyyMMdd')"
    $Operation = "read"
} else {
    $ProtocolId = "EXT-BS-RANDWRITE-002"
    $DefaultLabel = "block_size_randwrite_32g_$(Get-Date -Format 'yyyyMMdd')"
    $Operation = "write"
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
if ($Workload -eq "randwrite" -and -not $ConfirmDedicatedFileWrite) {
    throw "randwrite requires -ConfirmDedicatedFileWrite for the dedicated test file."
}
$DutPreflight = Assert-ExternalSsdTarget `
    -TestFile $TestFile `
    -IdentityConfigPath $DutIdentityConfig `
    -RequireExistingTarget `
    -ExpectedFileBytes $ExpectedBytes
$TestFile = $DutPreflight.canonical_target
if (-not (Test-Path -LiteralPath $ObserverScript)) {
    throw "Observer script not found: $ObserverScript"
}
if ($null -eq (Get-Command fio -ErrorAction SilentlyContinue)) {
    throw "fio command not found. Check PATH before starting the block-size sweep."
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

$PhaseSpecs = @(
    [ordered]@{ order = 1; cycle = 1; position = 1; block_size = "4k" },
    [ordered]@{ order = 2; cycle = 1; position = 2; block_size = "64k" },
    [ordered]@{ order = 3; cycle = 1; position = 3; block_size = "1m" },
    [ordered]@{ order = 4; cycle = 2; position = 1; block_size = "64k" },
    [ordered]@{ order = 5; cycle = 2; position = 2; block_size = "1m" },
    [ordered]@{ order = 6; cycle = 2; position = 3; block_size = "4k" },
    [ordered]@{ order = 7; cycle = 3; position = 1; block_size = "1m" },
    [ordered]@{ order = 8; cycle = 3; position = 2; block_size = "4k" },
    [ordered]@{ order = 9; cycle = 3; position = 3; block_size = "64k" }
)

$CycleSequences = @()
foreach ($CycleNumber in 1..3) {
    $Sequence = @(
        $PhaseSpecs |
            Where-Object { $_.cycle -eq $CycleNumber } |
            Sort-Object position |
            ForEach-Object { $_.block_size }
    )
    $CycleSequences += [ordered]@{ cycle = $CycleNumber; sequence = $Sequence }
}

$Phases = @()
foreach ($Spec in $PhaseSpecs) {
    $Phases += [pscustomobject][ordered]@{
        order = $Spec.order
        cycle = $Spec.cycle
        position = $Spec.position
        block_size = $Spec.block_size
        test_case_id = $ProtocolId
        workload = $Workload
        status = "planned"
        started_at = $null
        completed_at = $null
        fio_json = $null
        log_prefix = $null
    }
}

$Manifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeExperiment
    test_protocol_id = $ProtocolId
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_block_size_sweep.ps1"
    safety = "canonical existing 32 GiB file target on the enrolled DUT; no raw physical-drive target"
    dut_preflight = $DutPreflight
    question = "How do bandwidth, IOPS, and tail latency change across 4K, 64K, and 1M random $Operation I/O when each block size occupies each sequence position once?"
    experimental_unit = "one three-phase cycle; three Latin-square cycles form one workload session"
    interpretation_boundary = "Random file-target block-size mapping over USB, Windows, and exFAT; read and write sessions are independent observations and do not prove device-internal causes."
    fixed_controls = [ordered]@{
        reconnect_start_confirmed = [bool]$ConfirmReconnectStart
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_file_write_confirmed = [bool]$ConfirmDedicatedFileWrite
        user_confirmed_disconnect_sec = $ConfirmedDisconnectMinutes * 60
        test_file = $TestFile
        observed_file_bytes = $TargetFile.Length
        workload = $Workload
        operation = $Operation
        cycles = $CycleSequences
        block_sizes = @("4k", "64k", "1m")
        iodepth = 32
        size = "32G"
        runtime_sec = $RuntimeSec
        time_based = $true
        direct = 1
        numjobs = 1
        ioengine = "windowsaio"
        randrepeat = 1
        initial_idle_sec = $InitialIdleMinutes * 60
        inter_phase_idle_sec = $InterPhaseIdleSec
        read_only = ($Workload -eq "randread")
    }
    analysis_plan = @(
        "report bandwidth, IOPS, p99, p99.9, and maximum latency for each block size",
        "report repeat variation across the three cycle/position placements",
        "retain cycle and position to expose order effects",
        "compare read and write sessions descriptively only after both complete",
        "do not compare 4K random and 1M sequential evidence as if block size were the only variable",
        "do not claim internal cache, firmware, FTL, GC, NAND, thermal, or USB root cause"
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
    runner = "scripts/runners/run_external_ssd_block_size_sweep.ps1"
    safety = "time-based fio file-target runner; no raw physical-drive target"
    dut_preflight = $DutPreflight
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
    $env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "block_size_$Workload"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RW = $Workload
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = $RuntimeSec.ToString()
    $env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "32G"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_BS = "4k_64k_1m"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "32"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = "9"
    $env:SSD_LAB_EXTERNAL_TEST_CASE_ID = $ProtocolId
    $env:SSD_LAB_EXTERNAL_EXPERIMENT_ID = $SafeExperiment
    $env:SSD_LAB_EXTERNAL_STATE_PHASE = "counterbalanced_block_size_sweep"

    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunLabel -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Observer $Phase failed with exit code $LASTEXITCODE"
    }
}

Save-ExperimentManifest
Save-RunnerManifest

Write-Host "=== External SSD counterbalanced block-size sweep ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Protocol   : $ProtocolId"
Write-Host "Workload   : $Workload"
Write-Host "Test file  : $TestFile"
foreach ($Cycle in $CycleSequences) {
    Write-Host "Cycle $($Cycle.cycle)    : $($Cycle.sequence -join ' -> ')"
}
Write-Host "Condition  : random I/O, QD32, 32G, direct=1, $RuntimeSec seconds"
Write-Host "Start idle : $InitialIdleMinutes minutes"
Write-Host "Phase idle : $InterPhaseIdleSec seconds"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    Write-Host "[observer] Collecting pre-session evidence before controlled idle"
    Invoke-Observer -Phase "pre"

    if ($InitialIdleMinutes -gt 0) {
        Write-Host "[idle] Waiting $InitialIdleMinutes minutes before phase 1"
        Start-Sleep -Seconds ($InitialIdleMinutes * 60)
    }

    foreach ($Phase in $Phases) {
        $Order = $Phase.order
        $Cycle = $Phase.cycle
        $Position = $Phase.position
        $BlockSize = $Phase.block_size
        $BlockCode = $BlockSize.ToLowerInvariant()
        $OutFile = Join-Path $ResultDir "${RunLabel}_phase${Order}_c${Cycle}p${Position}_bs${BlockCode}.json"
        $LogPrefix = Join-Path $ResultDir "${RunLabel}_phase${Order}_c${Cycle}p${Position}_bs${BlockCode}"
        $RunRecord = [ordered]@{
            phase_order = $Order
            cycle = $Cycle
            position = $Position
            workload = $Workload
            operation = $Operation
            block_size = $BlockSize
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

        Write-Host "[phase $Order/9] cycle $Cycle position $Position - $Workload $BlockSize"
        $FioArgs = @(
            "--name=bs_sweep_${Workload}_c${Cycle}p${Position}_${BlockCode}",
            "--filename=$TestFile",
            "--rw=$Workload",
            "--bs=$BlockSize",
            "--iodepth=32",
            "--size=32G",
            "--runtime=$RuntimeSec",
            "--time_based=1",
            "--direct=1",
            "--ioengine=windowsaio",
            "--numjobs=1",
            "--thread=1",
            "--randrepeat=1",
            "--group_reporting=1",
            "--log_avg_msec=1000",
            "--write_bw_log=$LogPrefix",
            "--write_iops_log=$LogPrefix",
            "--write_lat_log=$LogPrefix",
            "--output-format=json",
            "--output=$OutFile"
        )
        if ($Workload -eq "randread") {
            $FioArgs += "--readonly"
        } else {
            $FioArgs += "--overwrite=1"
        }

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
        $PrimaryBytes = if ($Workload -eq "randread") { $Job.read.io_bytes } else { $Job.write.io_bytes }
        $OppositeBytes = if ($Workload -eq "randread") { $Job.write.io_bytes } else { $Job.read.io_bytes }
        if ($PrimaryBytes -le 0 -or $OppositeBytes -ne 0) {
            throw "Phase $Order did not preserve the expected $Workload direction."
        }

        $Phase.status = "complete"
        $Phase.completed_at = $RunRecord.completed_at
        Save-ExperimentManifest

        if ($Order -lt 9 -and $InterPhaseIdleSec -gt 0) {
            Write-Host "[idle] Waiting $InterPhaseIdleSec seconds before the next phase"
            Start-Sleep -Seconds $InterPhaseIdleSec
        }
    }

    $RunnerManifest.completed_at = (Get-Date).ToString("o")
    $RunnerManifest.status = "complete"
    Save-RunnerManifest

    Write-Host "[observer] Collecting post-session evidence"
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

Write-Host "=== External SSD block-size sweep completed ==="
Write-Host "Expected fio JSON files: 9"
Write-Host "Actual fio JSON files  : $((Get-ChildItem -LiteralPath $ResultDir -Filter '*_phase*_c*p*_bs*.json').Count)"
Write-Host "Result directory       : $ResultDir"
Write-Host "Runner manifest        : $RunnerManifestPath"
Write-Host "Experiment manifest    : $ExperimentManifestPath"
