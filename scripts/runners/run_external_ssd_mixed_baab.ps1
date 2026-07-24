# scripts/runners/run_external_ssd_mixed_baab.ps1
#
# Purpose:
#   Run an independent reconnect-start B-A-A-B sequence that reverses the
#   prior ABBA order under matched 4K, QD16, 32 GiB conditions.
#
# A = 100% randread
# B = randrw with 70% reads and 30% writes

param(
    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_seq_32g",

    [ValidateRange(1, 1440)]
    [int]$ConfirmedDisconnectMinutes = 10,

    [ValidateRange(0, 60)]
    [int]$InitialIdleMinutes = 5,

    [ValidateRange(1, 86400)]
    [int]$RuntimeSec = 180,

    [ValidateRange(0, 3600)]
    [int]$InterPhaseIdleSec = 60,

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
$ProtocolId = "EXT-MIXED-READ-QOS-BAAB-002"

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = "mixed_read_qos_baab_32g_$(Get-Date -Format 'yyyyMMdd')"
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
    throw "Re-run with -ConfirmDedicatedFileWrite after confirming B-phase writes to the dedicated file."
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
    throw "fio command not found. Check PATH before starting the BAAB sequence."
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

$PhaseSpecs = @(
    [ordered]@{ order = 1; code = "B1"; workload = "mixed_7030"; rw = "randrw" },
    [ordered]@{ order = 2; code = "A1"; workload = "pure_randread"; rw = "randread" },
    [ordered]@{ order = 3; code = "A2"; workload = "pure_randread"; rw = "randread" },
    [ordered]@{ order = 4; code = "B2"; workload = "mixed_7030"; rw = "randrw" }
)

$Phases = @()
foreach ($Spec in $PhaseSpecs) {
    $Phases += [pscustomobject][ordered]@{
        order = $Spec.order
        code = $Spec.code
        state_phase = "baab_$($Spec.code.ToLower())"
        test_case_id = if ($Spec.rw -eq "randread") {
            "EXT-MIXED-BAAB-PURE-READ"
        } else {
            "EXT-MIXED-BAAB-7030"
        }
        workload = $Spec.workload
        rw = $Spec.rw
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
    reference_experiment_id = "mixed_read_qos_abba_32g_20260724"
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_mixed_baab.ps1"
    safety = "existing dedicated 32 GiB file target under E:\validation; no raw physical-drive target"
    question = "Does an independent reconnect-start B-A-A-B session reproduce mixed read-QoS behavior after reversing the workload order?"
    experimental_unit = "one independently initiated B1-A1-A2-B2 sequence"
    interpretation_boundary = "Reconnect-start and same-port use are user-confirmed external conditions, not proof of an internally reset SSD state or device-internal behavior."
    fixed_controls = [ordered]@{
        reconnect_start_confirmed = [bool]$ConfirmReconnectStart
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_file_write_confirmed = [bool]$ConfirmDedicatedFileWrite
        user_confirmed_disconnect_sec = $ConfirmedDisconnectMinutes * 60
        test_file = $TestFile
        observed_file_bytes = $TargetFile.Length
        sequence = @("B1", "A1", "A2", "B2")
        A = "100% randread"
        B = "randrw 70% read / 30% write"
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
    }
    sweep_gate = [ordered]@{
        next_protocol = "EXT-MIXED-RATIO-SWEEP-001"
        proceed_if = "ABBA and BAAB together separate sequence position from repeatable read-QoS direction; otherwise investigate session state before sweeping ratios."
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
    runner = "scripts/runners/run_external_ssd_mixed_baab.ps1"
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
    $env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "mixed_read_qos_baab"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RW = "baab_randread_randrw"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = $RuntimeSec.ToString()
    $env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "32G"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_BS = "4k"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "16"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = "4"
    $env:SSD_LAB_EXTERNAL_TEST_CASE_ID = $ProtocolId
    $env:SSD_LAB_EXTERNAL_EXPERIMENT_ID = $SafeExperiment
    $env:SSD_LAB_EXTERNAL_STATE_PHASE = "baab_sequence"

    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunLabel -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Observer $Phase failed with exit code $LASTEXITCODE"
    }
}

Save-ExperimentManifest
Save-RunnerManifest

Write-Host "=== External SSD independent mixed read-QoS BAAB experiment ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Result set : $RunLabel"
Write-Host "Test file  : $TestFile"
Write-Host "Sequence   : B1 70:30 -> A1 pure read -> A2 pure read -> B2 70:30"
Write-Host "Disconnect : $ConfirmedDisconnectMinutes minutes (user confirmed)"
Write-Host "Runtime    : $RuntimeSec seconds per phase"
Write-Host "Start idle : $InitialIdleMinutes minutes"
Write-Host "Phase idle : $InterPhaseIdleSec seconds"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    if ($InitialIdleMinutes -gt 0) {
        Write-Host "[idle] Waiting $InitialIdleMinutes minutes before B1"
        Start-Sleep -Seconds ($InitialIdleMinutes * 60)
    }

    Write-Host "[observer] Collecting pre-sequence evidence"
    Invoke-Observer -Phase "pre"

    foreach ($Phase in $Phases) {
        $Order = $Phase.order
        $Code = $Phase.code
        $OutFile = Join-Path $ResultDir "${RunLabel}_phase${Order}_${Code}_run${Order}.json"
        $LogPrefix = Join-Path $ResultDir "${RunLabel}_phase${Order}_${Code}_run${Order}"
        $JobName = if ($Phase.rw -eq "randread") { "baab_${Code}_pure_read" } else { "baab_${Code}_mixed_7030" }
        $RunRecord = [ordered]@{
            phase_order = $Order
            phase_code = $Code
            workload = $Phase.workload
            rw = $Phase.rw
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

        Write-Host "[phase $Order/4] $Code - $($Phase.workload)"
        $FioArgs = @(
            "--name=$JobName",
            "--filename=$TestFile",
            "--rw=$($Phase.rw)",
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
            "--group_reporting=1",
            "--log_avg_msec=1000",
            "--write_bw_log=$LogPrefix",
            "--write_iops_log=$LogPrefix",
            "--write_lat_log=$LogPrefix",
            "--output-format=json",
            "--output=$OutFile"
        )

        if ($Phase.rw -eq "randread") {
            $FioArgs += "--readonly"
        } else {
            $FioArgs += "--rwmixread=70"
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
        if ($Job.read.io_bytes -le 0) {
            throw "Phase $Code did not record read I/O."
        }
        if ($Phase.rw -eq "randrw") {
            $TotalBytes = $Job.read.io_bytes + $Job.write.io_bytes
            $ReadShare = $Job.read.io_bytes / $TotalBytes
            if ($Job.write.io_bytes -le 0 -or [math]::Abs($ReadShare - 0.70) -gt 0.01) {
                throw "Phase $Code did not preserve the expected 70:30 read/write mix."
            }
        } elseif ($Job.write.io_bytes -ne 0) {
            throw "Pure-read phase $Code unexpectedly recorded write I/O."
        }

        $Phase.status = "complete"
        $Phase.completed_at = $RunRecord.completed_at
        Save-ExperimentManifest

        if ($Order -lt 4 -and $InterPhaseIdleSec -gt 0) {
            Write-Host "[idle] Waiting $InterPhaseIdleSec seconds before the next phase"
            Start-Sleep -Seconds $InterPhaseIdleSec
        }
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

Write-Host "=== Independent mixed read-QoS BAAB experiment completed ==="
Write-Host "Expected fio JSON files: 4"
Write-Host "Actual fio JSON files  : $((Get-ChildItem -LiteralPath $ResultDir -Filter '*_phase*_run*.json').Count)"
Write-Host "Result directory       : $ResultDir"
Write-Host "Runner manifest        : $RunnerManifestPath"
Write-Host "Experiment manifest    : $ExperimentManifestPath"
