# scripts/runners/run_external_ssd_large_ws_seq.ps1
#
# Purpose:
#   Execute one completion-based 32 GiB sequential write/read pilot against a
#   dedicated external-SSD file target with separate observer/runner evidence.
#
# Safety:
#   The target must be a new file under E:\validation. The script refuses an
#   existing target, creates and verifies the dedicated file before the idle
#   interval, requires at least 40 GiB free, and never uses a raw disk.

param(
    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_seq_32g",

    [ValidateRange(1, 60)]
    [int]$InitialIdleMinutes = 5,

    [ValidateRange(0, 3600)]
    [int]$ReadIdleSec = 60,

    [switch]$ConfirmSamePort,
    [switch]$ConfirmDedicatedFileWrite
)

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$ExperimentRoot = Join-Path $ResultRoot "_experiments"
$ObserverScript = Join-Path $BaseDir "scripts\observers\collect_external_ssd_observer.ps1"
$ExpectedBytes = 32GB
$RequiredFreeBytes = 40GB

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = "large_ws_seq_32g_$(Get-Date -Format 'yyyyMMdd')"
}

$SafeExperiment = $ExperimentLabel -replace '[^A-Za-z0-9_.-]', '_'
$ExperimentDir = Join-Path $ExperimentRoot $SafeExperiment
$ExperimentManifestPath = Join-Path $ExperimentDir "experiment_manifest.json"
$WriteRun = "sustained_${SafeExperiment}_seqwrite_32g_run1"
$ReadRun = "sustained_${SafeExperiment}_seqread_32g_run1"

if (-not $ConfirmSamePort) {
    throw "Re-run with -ConfirmSamePort after confirming the intended physical USB port."
}
if (-not $ConfirmDedicatedFileWrite) {
    throw "Re-run with -ConfirmDedicatedFileWrite after confirming that the dedicated 32 GiB file may be created."
}
if (-not ($TestFile -like "E:\validation\*")) {
    throw "TestFile must stay under E:\validation. Current: $TestFile"
}
if (Test-Path -LiteralPath $TestFile) {
    throw "Dedicated test file already exists. Do not overwrite it automatically: $TestFile"
}
if (-not (Test-Path -LiteralPath (Split-Path -Parent $TestFile))) {
    throw "Target directory does not exist: $(Split-Path -Parent $TestFile)"
}
if (-not (Test-Path -LiteralPath $ObserverScript)) {
    throw "Observer script not found: $ObserverScript"
}
if ($null -eq (Get-Command fio -ErrorAction SilentlyContinue)) {
    throw "fio command not found. Check PATH before the idle interval starts."
}
if (Test-Path -LiteralPath $ExperimentManifestPath) {
    throw "Experiment manifest already exists. Use a new ExperimentLabel: $ExperimentManifestPath"
}

$Volume = Get-Volume -DriveLetter E -ErrorAction Stop
if ($Volume.HealthStatus -ne "Healthy" -or $Volume.OperationalStatus -notcontains "OK") {
    throw "E: volume is not Healthy/OK. Health=$($Volume.HealthStatus), Operational=$($Volume.OperationalStatus)"
}
if ($Volume.SizeRemaining -lt $RequiredFreeBytes) {
    throw "At least 40 GiB free is required. Current free bytes: $($Volume.SizeRemaining)"
}

foreach ($runLabel in @($WriteRun, $ReadRun)) {
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
        state_phase = "large_ws_seq_write"
        test_case_id = "EXT-LARGE-WS-SEQ-WRITE-32G"
        run_id = $WriteRun
        status = "planned"
        started_at = $null
        completed_at = $null
    },
    [pscustomobject][ordered]@{
        order = 2
        state_phase = "large_ws_seq_read"
        test_case_id = "EXT-LARGE-WS-SEQ-READ-32G"
        run_id = $ReadRun
        status = "planned"
        started_at = $null
        completed_at = $null
    }
)

$Manifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeExperiment
    test_protocol_id = "EXT-LARGE-WS-SEQ-001"
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_large_ws_seq.ps1"
    safety = "dedicated file target under E:\validation; refuses existing target and raw physical-drive access"
    question = "Does sequential throughput remain stable while completing one 32 GiB write and one 32 GiB read?"
    interpretation_boundary = "USB, Windows, exFAT file-target result; any transition is externally observed and is not proof of cache, FTL, or garbage collection."
    fixed_controls = [ordered]@{
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_file_write_confirmed = [bool]$ConfirmDedicatedFileWrite
        test_file = $TestFile
        expected_file_bytes = $ExpectedBytes
        required_free_bytes = $RequiredFreeBytes
        initial_free_bytes = $Volume.SizeRemaining
        initial_idle_sec = $InitialIdleMinutes * 60
        read_idle_sec = $ReadIdleSec
        ioengine = "windowsaio"
        block_size = "1M"
        iodepth = 4
        direct = 1
        numjobs = 1
        execution_mode = "completion_based_overwrite"
    }
    target_preparation = [ordered]@{
        method = "dotnet_filestream_create_new_set_length"
        started_at = $null
        completed_at = $null
        status = "planned"
        observed_file_bytes = $null
    }
    observed_file_bytes_after_write = $null
    observed_file_bytes_after_read = $null
    phases = $Phases
    error = $null
}

function Save-Json {
    param([object]$Value, [string]$Path)
    $Value | ConvertTo-Json -Depth 10 | Out-File -FilePath $Path -Encoding utf8
}

function Save-ExperimentManifest {
    Save-Json -Value $Manifest -Path $ExperimentManifestPath
}

function Initialize-DedicatedTestFile {
    $Manifest.target_preparation.status = "running"
    $Manifest.target_preparation.started_at = (Get-Date).ToString("o")
    Save-ExperimentManifest

    $Stream = $null
    try {
        $Stream = [System.IO.FileStream]::new(
            $TestFile,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        $Stream.SetLength($ExpectedBytes)
        $Stream.Flush($true)
    }
    finally {
        if ($null -ne $Stream) {
            $Stream.Dispose()
        }
    }

    $PreparedFile = Get-Item -LiteralPath $TestFile -ErrorAction Stop
    $Manifest.target_preparation.observed_file_bytes = $PreparedFile.Length
    $Manifest.target_preparation.completed_at = (Get-Date).ToString("o")
    if ($PreparedFile.Length -ne $ExpectedBytes) {
        $Manifest.target_preparation.status = "failed"
        Save-ExperimentManifest
        throw "Dedicated file preparation produced an unexpected length. Expected=$ExpectedBytes, actual=$($PreparedFile.Length)"
    }

    $Manifest.target_preparation.status = "complete"
    Save-ExperimentManifest
}

function Invoke-Observer {
    param([string]$RunLabel, [string]$Phase)

    $env:SSD_LAB_EXTERNAL_TESTFILE = $TestFile
    $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL = $RunLabel
    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunLabel -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Observer $Phase failed for $RunLabel with exit code $LASTEXITCODE"
    }
}

function Invoke-SequentialPhase {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Phase,
        [Parameter(Mandatory = $true)]
        [ValidateSet("write", "read")]
        [string]$Rw
    )

    $RunLabel = $Phase.run_id
    $ResultDir = Join-Path $ResultRoot $RunLabel
    $RunnerManifestPath = Join-Path $ResultDir "runner_manifest.json"
    $OutFile = Join-Path $ResultDir "${RunLabel}_run1.json"
    $LogPrefix = Join-Path $ResultDir "${RunLabel}_run1"
    $Workload = if ($Rw -eq "write") { "seq_write" } else { "seq_read" }
    $ReadOnly = $Rw -eq "read"

    New-Item -ItemType Directory -Force $ResultDir | Out-Null
    $Phase.status = "running"
    $Phase.started_at = (Get-Date).ToString("o")
    Save-ExperimentManifest

    $RunnerManifest = [ordered]@{
        schema_version = "1.0"
        role = "runner"
        run_id = $RunLabel
        test_case_id = $Phase.test_case_id
        experiment_id = $SafeExperiment
        state_phase = $Phase.state_phase
        started_at = (Get-Date).ToString("o")
        completed_at = $null
        status = "started"
        runner = "scripts/runners/run_external_ssd_large_ws_seq.ps1"
        safety = "completion-based fio file-target runner; no raw physical-drive target"
        result_dir = $ResultDir
        test_file = $TestFile
        conditions = [ordered]@{
            workload = $Workload
            rw = $Rw
            bs = "1M"
            iodepth = 4
            size = "32G"
            planned_bytes = $ExpectedBytes
            direct = 1
            numjobs = 1
            ioengine = "windowsaio"
            time_based = $false
            overwrite = $true
            readonly = $ReadOnly
            planned_runs = 1
        }
        runs = @()
    }
    Save-Json -Value $RunnerManifest -Path $RunnerManifestPath

    Invoke-Observer -RunLabel $RunLabel -Phase "pre"

    $RunRecord = [ordered]@{
        run = 1
        started_at = (Get-Date).ToString("o")
        completed_at = $null
        status = "started"
        exit_code = $null
        fio_json = $OutFile
        log_prefix = $LogPrefix
    }

    $fioArgs = @(
        "--name=$Workload",
        "--filename=$TestFile",
        "--rw=$Rw",
        "--bs=1M",
        "--iodepth=4",
        "--size=32G",
        "--numjobs=1",
        "--ioengine=windowsaio",
        "--direct=1",
        "--thread=1",
        "--overwrite=1",
        "--group_reporting=1",
        "--log_avg_msec=1000",
        "--write_bw_log=$LogPrefix",
        "--write_iops_log=$LogPrefix",
        "--write_lat_log=$LogPrefix",
        "--output-format=json",
        "--output=$OutFile"
    )
    if ($ReadOnly) {
        $fioArgs += "--readonly"
    }

    Write-Host "=== Running ${Workload}: 32 GiB completion-based ==="
    & fio @fioArgs
    $FioExitCode = $LASTEXITCODE

    $RunRecord.completed_at = (Get-Date).ToString("o")
    $RunRecord.exit_code = $FioExitCode
    $RunRecord.status = if ($FioExitCode -eq 0) { "complete" } else { "failed" }
    $RunnerManifest.runs += $RunRecord
    $RunnerManifest.completed_at = (Get-Date).ToString("o")
    $RunnerManifest.status = $RunRecord.status
    Save-Json -Value $RunnerManifest -Path $RunnerManifestPath

    Invoke-Observer -RunLabel $RunLabel -Phase "post"

    if ($FioExitCode -ne 0) {
        throw "fio $Workload failed with exit code $FioExitCode"
    }
    if (-not (Test-Path -LiteralPath $OutFile)) {
        throw "fio JSON was not created: $OutFile"
    }
    if (-not (Test-Path -LiteralPath $TestFile)) {
        throw "Dedicated target file is missing after fio $Workload completed: $TestFile"
    }

    $Phase.status = "complete"
    $Phase.completed_at = (Get-Date).ToString("o")
    Save-ExperimentManifest
}

Save-ExperimentManifest

Write-Host "=== External SSD 32 GiB sequential pilot ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Test file  : $TestFile"
Write-Host "Free GiB   : $([math]::Round($Volume.SizeRemaining / 1GB, 2))"
Write-Host "Sequence   : prepare 32G file -> 5m idle -> 32G seqwrite -> 60s idle -> 32G seqread"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    Write-Host "[setup] Creating and verifying the dedicated 32 GiB target"
    Initialize-DedicatedTestFile

    $InitialIdleSec = $InitialIdleMinutes * 60
    Write-Host "[1/4] Initial idle interval: $InitialIdleSec seconds"
    Start-Sleep -Seconds $InitialIdleSec

    Write-Host "[2/4] Sequential write: 32 GiB, bs=1M, QD4"
    Invoke-SequentialPhase -Phase $Phases[0] -Rw "write"

    $WriteFile = Get-Item -LiteralPath $TestFile -ErrorAction Stop
    $Manifest.observed_file_bytes_after_write = $WriteFile.Length
    Save-ExperimentManifest
    if ($WriteFile.Length -ne $ExpectedBytes) {
        throw "Unexpected file size after write. Expected=$ExpectedBytes, actual=$($WriteFile.Length)"
    }

    Write-Host "[3/4] Pre-read idle interval: $ReadIdleSec seconds"
    Start-Sleep -Seconds $ReadIdleSec

    Write-Host "[4/4] Sequential read: 32 GiB, bs=1M, QD4"
    Invoke-SequentialPhase -Phase $Phases[1] -Rw "read"

    $ReadFile = Get-Item -LiteralPath $TestFile -ErrorAction Stop
    $Manifest.observed_file_bytes_after_read = $ReadFile.Length
    if ($ReadFile.Length -ne $ExpectedBytes) {
        throw "Unexpected file size after read. Expected=$ExpectedBytes, actual=$($ReadFile.Length)"
    }

    $Manifest.completed_at = (Get-Date).ToString("o")
    $Manifest.status = "complete"
    Save-ExperimentManifest
}
catch {
    if ($Manifest.target_preparation.status -eq "running") {
        $Manifest.target_preparation.status = "failed"
        $Manifest.target_preparation.completed_at = (Get-Date).ToString("o")
    }
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

Write-Host "=== 32 GiB sequential pilot completed ==="
Write-Host "The dedicated 32 GiB file is retained for evidence and follow-up read/verify work."
Write-Host "Experiment manifest: $ExperimentManifestPath"
