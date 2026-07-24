# scripts/runners/run_external_ssd_mixed_abba.ps1
#
# Purpose:
#   Run an A-B-B-A sequence to test whether adding 30% random writes inflates
#   read QoS under matched 4K, QD16, 32 GiB conditions.
#
# A = 100% randread
# B = randrw with 70% reads and 30% writes
#
# Safety:
#   The runner requires an existing exact-size file under E:\validation,
#   explicit same-port and write confirmations, and never targets a raw disk.

param(
    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_seq_32g",

    [ValidateRange(0, 60)]
    [int]$InitialIdleMinutes = 5,

    [ValidateRange(1, 86400)]
    [int]$RuntimeSec = 180,

    [ValidateRange(0, 3600)]
    [int]$InterPhaseIdleSec = 60,

    [switch]$ConfirmSamePort,
    [switch]$ConfirmDedicatedFileWrite
)

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$ExperimentRoot = Join-Path $ResultRoot "_experiments"
$ObserverScript = Join-Path $BaseDir "scripts\observers\collect_external_ssd_observer.ps1"
$ExpectedBytes = 32GB

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = "mixed_read_qos_abba_32g_$(Get-Date -Format 'yyyyMMdd')"
}

$SafeExperiment = $ExperimentLabel -replace '[^A-Za-z0-9_.-]', '_'
$RunLabel = "sustained_${SafeExperiment}"
$ResultDir = Join-Path $ResultRoot $RunLabel
$RunnerManifestPath = Join-Path $ResultDir "runner_manifest.json"
$ExperimentDir = Join-Path $ExperimentRoot $SafeExperiment
$ExperimentManifestPath = Join-Path $ExperimentDir "experiment_manifest.json"

if (-not $ConfirmSamePort) {
    throw "Re-run with -ConfirmSamePort after confirming the intended physical USB port."
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
    throw "fio command not found. Check PATH before starting the ABBA sequence."
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
    [ordered]@{ order = 1; code = "A1"; workload = "pure_randread"; rw = "randread"; rwmixread = $null },
    [ordered]@{ order = 2; code = "B1"; workload = "mixed_7030"; rw = "randrw"; rwmixread = 70 },
    [ordered]@{ order = 3; code = "B2"; workload = "mixed_7030"; rw = "randrw"; rwmixread = 70 },
    [ordered]@{ order = 4; code = "A2"; workload = "pure_randread"; rw = "randread"; rwmixread = $null }
)

$Phases = @()
foreach ($Spec in $PhaseSpecs) {
    $Phases += [pscustomobject][ordered]@{
        order = $Spec.order
        code = $Spec.code
        state_phase = "abba_$($Spec.code.ToLower())"
        test_case_id = if ($Spec.rw -eq "randread") {
            "EXT-MIXED-ABBA-PURE-READ"
        } else {
            "EXT-MIXED-ABBA-7030"
        }
        workload = $Spec.workload
        rw = $Spec.rw
        rwmixread = $Spec.rwmixread
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
    test_protocol_id = "EXT-MIXED-READ-QOS-ABBA-001"
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_mixed_abba.ps1"
    safety = "existing dedicated 32 GiB file target under E:\validation; no raw physical-drive target"
    question = "Does adding 30% random writes inflate read p99/p99.9 under matched QD16 conditions after controlling sequence position with A-B-B-A?"
    experimental_unit = "one connected-session A1-B1-B2-A2 sequence"
    interpretation_boundary = "ABBA controls first/last sequence position inside one session but is not an independent reconnect replicate or proof of device-internal behavior."
    fixed_controls = [ordered]@{
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_file_write_confirmed = [bool]$ConfirmDedicatedFileWrite
        test_file = $TestFile
        observed_file_bytes = $TargetFile.Length
        sequence = @("A1", "B1", "B2", "A2")
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
        proceed_if = "A1 and A2 are sufficiently comparable and B1/B2 show repeatable read-QoS inflation; otherwise investigate carry-over or session state first."
    }
    phases = $Phases
    error = $null
}

$RunnerManifest = [ordered]@{
    schema_version = "1.0"
    role = "runner"
    run_id = $RunLabel
    test_case_id = "EXT-MIXED-READ-QOS-ABBA-001"
    experiment_id = $SafeExperiment
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    runner = "scripts/runners/run_external_ssd_mixed_abba.ps1"
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
    $env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "mixed_read_qos_abba"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RW = "abba_randread_randrw"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = $RuntimeSec.ToString()
    $env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "32G"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_BS = "4k"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "16"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = "4"
    $env:SSD_LAB_EXTERNAL_TEST_CASE_ID = "EXT-MIXED-READ-QOS-ABBA-001"
    $env:SSD_LAB_EXTERNAL_EXPERIMENT_ID = $SafeExperiment
    $env:SSD_LAB_EXTERNAL_STATE_PHASE = "abba_sequence"

    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunLabel -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Observer $Phase failed with exit code $LASTEXITCODE"
    }
}

Save-ExperimentManifest
Save-RunnerManifest

Write-Host "=== External SSD mixed read-QoS ABBA experiment ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Result set : $RunLabel"
Write-Host "Test file  : $TestFile"
Write-Host "Sequence   : A1 pure read -> B1 70:30 -> B2 70:30 -> A2 pure read"
Write-Host "Runtime    : $RuntimeSec seconds per phase"
Write-Host "Start idle : $InitialIdleMinutes minutes"
Write-Host "Phase idle : $InterPhaseIdleSec seconds"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    if ($InitialIdleMinutes -gt 0) {
        Write-Host "[idle] Waiting $InitialIdleMinutes minutes before A1"
        Start-Sleep -Seconds ($InitialIdleMinutes * 60)
    }

    Write-Host "[observer] Collecting pre-sequence evidence"
    Invoke-Observer -Phase "pre"

    foreach ($Phase in $Phases) {
        $Order = $Phase.order
        $Code = $Phase.code
        $OutFile = Join-Path $ResultDir "${RunLabel}_phase${Order}_${Code}_run${Order}.json"
        $LogPrefix = Join-Path $ResultDir "${RunLabel}_phase${Order}_${Code}_run${Order}"
        $JobName = if ($Phase.rw -eq "randread") { "abba_${Code}_pure_read" } else { "abba_${Code}_mixed_7030" }
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

Write-Host "=== Mixed read-QoS ABBA experiment completed ==="
Write-Host "Expected fio JSON files: 4"
Write-Host "Actual fio JSON files  : $((Get-ChildItem -LiteralPath $ResultDir -Filter '*_phase*_run*.json').Count)"
Write-Host "Result directory       : $ResultDir"
Write-Host "Runner manifest        : $RunnerManifestPath"
Write-Host "Experiment manifest    : $ExperimentManifestPath"
