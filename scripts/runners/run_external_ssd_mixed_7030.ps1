# scripts/runners/run_external_ssd_mixed_7030.ps1
#
# Purpose:
#   Execute a controlled 4K random mixed read/write 70:30 workload against the
#   existing dedicated 32 GiB external-SSD file target.
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

    [ValidateRange(1, 100)]
    [int]$Runs = 3,

    [ValidateRange(0, 3600)]
    [int]$InterRunIdleSec = 60,

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

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = "mixed_7030_32g_$(Get-Date -Format 'yyyyMMdd')"
}

$SafeExperiment = $ExperimentLabel -replace '[^A-Za-z0-9_.-]', '_'
$RunLabel = "sustained_${SafeExperiment}_randrw_7030_4k_qd16_repeat${Runs}"
$ResultDir = Join-Path $ResultRoot $RunLabel
$ExperimentDir = Join-Path $ExperimentRoot $SafeExperiment
$ExperimentManifestPath = Join-Path $ExperimentDir "experiment_manifest.json"
$RunnerManifestPath = Join-Path $ResultDir "runner_manifest.json"

if (-not $ConfirmSamePort) {
    throw "Re-run with -ConfirmSamePort after confirming the intended physical USB port."
}
if (-not $ConfirmDedicatedFileWrite) {
    throw "Re-run with -ConfirmDedicatedFileWrite after confirming mixed writes to the dedicated file."
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
    throw "fio command not found. Check PATH before starting the workload."
}
if (Test-Path -LiteralPath $ExperimentManifestPath) {
    throw "Experiment manifest already exists. Use a new ExperimentLabel: $ExperimentManifestPath"
}
if (Test-Path -LiteralPath $ResultDir) {
    $ExistingRuns = @(Get-ChildItem -LiteralPath $ResultDir -Filter "*_run*.json" -ErrorAction SilentlyContinue)
    if ($ExistingRuns.Count -gt 0) {
        throw "Result directory already contains fio JSON. Use a new ExperimentLabel: $ResultDir"
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

$Phases = @()
for ($Run = 1; $Run -le $Runs; $Run++) {
    $Phases += [pscustomobject][ordered]@{
        order = $Run
        state_phase = "mixed_7030_run${Run}"
        test_case_id = "EXT-MIXED-RW-7030-4K-QD16"
        run = $Run
        status = "planned"
        started_at = $null
        completed_at = $null
    }
}

$Manifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeExperiment
    test_protocol_id = "EXT-MIXED-RW-7030-001"
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_mixed_7030.ps1"
    safety = "canonical existing 32 GiB file target on the enrolled DUT; no raw physical-drive target"
    dut_preflight = $DutPreflight
    question = "How do read and write throughput and tail latency behave when 4K random reads and writes are issued concurrently at a synthetic 70:30 ratio?"
    interpretation_boundary = "Synthetic USB, Windows, exFAT file-target workload; it is not a customer trace and does not prove cache, FTL, GC, or NAND behavior."
    fixed_controls = [ordered]@{
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_file_write_confirmed = [bool]$ConfirmDedicatedFileWrite
        test_file = $TestFile
        observed_file_bytes = $TargetFile.Length
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
        planned_runs = $Runs
        initial_idle_sec = $InitialIdleMinutes * 60
        inter_run_idle_sec = $InterRunIdleSec
    }
    phases = $Phases
    error = $null
}

$RunnerManifest = [ordered]@{
    schema_version = "1.0"
    role = "runner"
    run_id = $RunLabel
    test_case_id = "EXT-MIXED-RW-7030-4K-QD16"
    experiment_id = $SafeExperiment
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    runner = "scripts/runners/run_external_ssd_mixed_7030.ps1"
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
    $env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "mixed_7030"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RW = "randrw"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = $RuntimeSec.ToString()
    $env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "32G"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_BS = "4k"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "16"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = $Runs.ToString()
    $env:SSD_LAB_EXTERNAL_TEST_CASE_ID = "EXT-MIXED-RW-7030-4K-QD16"
    $env:SSD_LAB_EXTERNAL_EXPERIMENT_ID = $SafeExperiment
    $env:SSD_LAB_EXTERNAL_STATE_PHASE = "mixed_7030_repeat_set"

    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunLabel -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Observer $Phase failed with exit code $LASTEXITCODE"
    }
}

Save-ExperimentManifest
Save-RunnerManifest

Write-Host "=== External SSD mixed 70:30 workload ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Result set : $RunLabel"
Write-Host "Test file  : $TestFile"
Write-Host "Workload   : randrw, read=70%, write=30%, 4k, QD16"
Write-Host "Runtime    : $RuntimeSec seconds x $Runs runs"
Write-Host "Start idle : $InitialIdleMinutes minutes"
Write-Host "Idle       : $InterRunIdleSec seconds between runs"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    if ($InitialIdleMinutes -gt 0) {
        Write-Host "[idle] Waiting $InitialIdleMinutes minutes before the repeat set"
        Start-Sleep -Seconds ($InitialIdleMinutes * 60)
    }

    Write-Host "[observer] Collecting pre-run evidence"
    Invoke-Observer -Phase "pre"

    for ($Run = 1; $Run -le $Runs; $Run++) {
        $Phase = $Phases[$Run - 1]
        $OutFile = Join-Path $ResultDir "${RunLabel}_run${Run}.json"
        $LogPrefix = Join-Path $ResultDir "${RunLabel}_run${Run}"
        $RunRecord = [ordered]@{
            run = $Run
            started_at = (Get-Date).ToString("o")
            completed_at = $null
            status = "started"
            exit_code = $null
            fio_json = $OutFile
            log_prefix = $LogPrefix
        }

        $Phase.status = "running"
        $Phase.started_at = $RunRecord.started_at
        Save-ExperimentManifest

        Write-Host "[run $Run/$Runs] 4K randrw 70:30, QD16, ${RuntimeSec}s"
        $FioArgs = @(
            "--name=mixed_7030",
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
            "--overwrite=1",
            "--randrepeat=1",
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
            throw "fio mixed run $Run failed with exit code $FioExitCode"
        }
        if (-not (Test-Path -LiteralPath $OutFile)) {
            throw "fio JSON was not created: $OutFile"
        }
        if (-not (Test-Path -LiteralPath $TestFile)) {
            throw "Dedicated target file is missing after run ${Run}: $TestFile"
        }

        $Job = (Get-Content -Raw -LiteralPath $OutFile | ConvertFrom-Json).jobs[0]
        if ($Job.error -ne 0) {
            throw "fio JSON reports error=$($Job.error) for run $Run"
        }
        if ($Job.read.io_bytes -le 0 -or $Job.write.io_bytes -le 0) {
            throw "Mixed run $Run did not record both read and write I/O."
        }

        $Phase.status = "complete"
        $Phase.completed_at = $RunRecord.completed_at
        Save-ExperimentManifest

        if ($Run -lt $Runs -and $InterRunIdleSec -gt 0) {
            Write-Host "[idle] Waiting $InterRunIdleSec seconds before run $($Run + 1)"
            Start-Sleep -Seconds $InterRunIdleSec
        }
    }

    $RunnerManifest.completed_at = (Get-Date).ToString("o")
    $RunnerManifest.status = "complete"
    Save-RunnerManifest

    Write-Host "[observer] Collecting post-run evidence"
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

Write-Host "=== Mixed 70:30 workload completed ==="
Write-Host "Expected JSON files: $Runs"
Write-Host "Actual JSON files  : $((Get-ChildItem -LiteralPath $ResultDir -Filter '*_run*.json').Count)"
Write-Host "Result directory   : $ResultDir"
Write-Host "Runner manifest    : $RunnerManifestPath"
Write-Host "Experiment manifest: $ExperimentManifestPath"
