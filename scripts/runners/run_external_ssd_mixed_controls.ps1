# scripts/runners/run_external_ssd_mixed_controls.ps1
#
# Purpose:
#   Collect matched 100% random-read and 100% random-write controls for the
#   70:30 mixed workload using the same 32 GiB file and fio conditions.
#
# Safety:
#   The runner requires an existing exact-size file under E:\validation,
#   explicit same-port and write confirmations, and never targets a raw disk.

param(
    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_seq_32g",

    [ValidateRange(0, 60)]
    [int]$InitialIdleMinutes = 5,

    [ValidateRange(0, 60)]
    [int]$TransitionIdleMinutes = 5,

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
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$ExperimentRoot = Join-Path $ResultRoot "_experiments"
$ObserverScript = Join-Path $BaseDir "scripts\observers\collect_external_ssd_observer.ps1"
$ExpectedBytes = 32GB

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = "mixed_control_32g_$(Get-Date -Format 'yyyyMMdd')"
}

$SafeExperiment = $ExperimentLabel -replace '[^A-Za-z0-9_.-]', '_'
$ReadRunLabel = "sustained_${SafeExperiment}_randread_4k_qd16_repeat${Runs}"
$WriteRunLabel = "sustained_${SafeExperiment}_randwrite_4k_qd16_repeat${Runs}"
$ExperimentDir = Join-Path $ExperimentRoot $SafeExperiment
$ExperimentManifestPath = Join-Path $ExperimentDir "experiment_manifest.json"

if (-not $ConfirmSamePort) {
    throw "Re-run with -ConfirmSamePort after confirming the intended physical USB port."
}
if (-not $ConfirmDedicatedFileWrite) {
    throw "Re-run with -ConfirmDedicatedFileWrite after confirming writes to the dedicated file."
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
    throw "fio command not found. Check PATH before starting the controls."
}
if (Test-Path -LiteralPath $ExperimentManifestPath) {
    throw "Experiment manifest already exists. Use a new ExperimentLabel: $ExperimentManifestPath"
}

$TargetFile = Get-Item -LiteralPath $TestFile -ErrorAction Stop
if ($TargetFile.Length -ne $ExpectedBytes) {
    throw "Test file must be exactly 32 GiB. Expected=$ExpectedBytes, actual=$($TargetFile.Length)"
}

foreach ($RunLabel in @($ReadRunLabel, $WriteRunLabel)) {
    $ResultDir = Join-Path $ResultRoot $RunLabel
    if (Test-Path -LiteralPath $ResultDir) {
        $ExistingRuns = @(Get-ChildItem -LiteralPath $ResultDir -Filter "*_run*.json" -ErrorAction SilentlyContinue)
        if ($ExistingRuns.Count -gt 0) {
            throw "Result directory already contains fio JSON. Use a new ExperimentLabel: $ResultDir"
        }
    }
}

New-Item -ItemType Directory -Force $ExperimentDir | Out-Null

function Save-Json {
    param([object]$Value, [string]$Path)
    $Value | ConvertTo-Json -Depth 10 | Out-File -FilePath $Path -Encoding utf8
}

$Phases = @(
    [pscustomobject][ordered]@{
        order = 1
        state_phase = "pure_randread_control"
        test_case_id = "EXT-MIXED-CONTROL-RANDREAD-4K-QD16"
        run_id = $ReadRunLabel
        status = "planned"
        started_at = $null
        completed_at = $null
    },
    [pscustomobject][ordered]@{
        order = 2
        state_phase = "pure_randwrite_control"
        test_case_id = "EXT-MIXED-CONTROL-RANDWRITE-4K-QD16"
        run_id = $WriteRunLabel
        status = "planned"
        started_at = $null
        completed_at = $null
    }
)

$Manifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeExperiment
    test_protocol_id = "EXT-MIXED-CONTROL-001"
    reference_experiment_id = "mixed_7030_32g_20260724"
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_mixed_controls.ps1"
    safety = "existing dedicated 32 GiB file target under E:\validation; no raw physical-drive target"
    question = "How do the 70:30 mixed results compare with matched 100% random-read and 100% random-write controls?"
    sequence_reason = "Read control runs first to avoid preceding it with the write-control workload."
    experimental_unit = "three process repeats per pure control inside one connected session"
    interpretation_boundary = "Matched synthetic controls on USB, Windows, and an exFAT file target; they are not independent reconnect sessions or proof of device-internal behavior."
    fixed_controls = [ordered]@{
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_file_write_confirmed = [bool]$ConfirmDedicatedFileWrite
        test_file = $TestFile
        observed_file_bytes = $TargetFile.Length
        block_size = "4k"
        iodepth = 16
        size = "32G"
        runtime_sec = $RuntimeSec
        time_based = $true
        direct = 1
        numjobs = 1
        ioengine = "windowsaio"
        randrepeat = 1
        planned_runs_per_control = $Runs
        initial_idle_sec = $InitialIdleMinutes * 60
        transition_idle_sec = $TransitionIdleMinutes * 60
        inter_run_idle_sec = $InterRunIdleSec
        control_order = @("randread", "randwrite")
    }
    phases = $Phases
    error = $null
}

function Save-ExperimentManifest {
    Save-Json -Value $Manifest -Path $ExperimentManifestPath
}

function Invoke-Observer {
    param(
        [string]$RunLabel,
        [string]$Workload,
        [string]$Rw,
        [string]$StatePhase,
        [string]$Phase
    )

    $env:SSD_LAB_EXTERNAL_TESTFILE = $TestFile
    $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL = $RunLabel
    $env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = $Workload
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RW = $Rw
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = $RuntimeSec.ToString()
    $env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "32G"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_BS = "4k"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "16"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
    $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = $Runs.ToString()
    $env:SSD_LAB_EXTERNAL_TEST_CASE_ID = if ($Rw -eq "randread") {
        "EXT-MIXED-CONTROL-RANDREAD-4K-QD16"
    } else {
        "EXT-MIXED-CONTROL-RANDWRITE-4K-QD16"
    }
    $env:SSD_LAB_EXTERNAL_EXPERIMENT_ID = $SafeExperiment
    $env:SSD_LAB_EXTERNAL_STATE_PHASE = $StatePhase

    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunLabel -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Observer $Phase failed for $RunLabel with exit code $LASTEXITCODE"
    }
}

function Invoke-ControlSet {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Phase,

        [Parameter(Mandatory = $true)]
        [ValidateSet("randread", "randwrite")]
        [string]$Rw
    )

    $RunLabel = $Phase.run_id
    $Workload = if ($Rw -eq "randread") { "control_rand_read" } else { "control_rand_write" }
    $ResultDir = Join-Path $ResultRoot $RunLabel
    $RunnerManifestPath = Join-Path $ResultDir "runner_manifest.json"
    $ReadOnly = $Rw -eq "randread"

    New-Item -ItemType Directory -Force $ResultDir | Out-Null

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
        runner = "scripts/runners/run_external_ssd_mixed_controls.ps1"
        safety = "time-based fio file-target runner; no raw physical-drive target"
        result_dir = $ResultDir
        test_file = $TestFile
        conditions = [ordered]@{
            workload = $Workload
            rw = $Rw
            bs = "4k"
            iodepth = 16
            size = "32G"
            runtime_sec = $RuntimeSec
            time_based = $true
            direct = 1
            numjobs = 1
            ioengine = "windowsaio"
            randrepeat = 1
            readonly = $ReadOnly
            planned_runs = $Runs
            inter_run_idle_sec = $InterRunIdleSec
        }
        runs = @()
    }

    $Phase.status = "running"
    $Phase.started_at = (Get-Date).ToString("o")
    Save-ExperimentManifest
    Save-Json -Value $RunnerManifest -Path $RunnerManifestPath

    try {
        Write-Host "[observer] Collecting pre evidence for $Rw"
        Invoke-Observer `
            -RunLabel $RunLabel `
            -Workload $Workload `
            -Rw $Rw `
            -StatePhase $Phase.state_phase `
            -Phase "pre"

        for ($Run = 1; $Run -le $Runs; $Run++) {
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

            Write-Host "[$Rw run $Run/$Runs] 4K, QD16, ${RuntimeSec}s"
            $FioArgs = @(
                "--name=$Workload",
                "--filename=$TestFile",
                "--rw=$Rw",
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

            if ($ReadOnly) {
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
            Save-Json -Value $RunnerManifest -Path $RunnerManifestPath

            if ($FioExitCode -ne 0) {
                throw "fio $Rw run $Run failed with exit code $FioExitCode"
            }
            if (-not (Test-Path -LiteralPath $OutFile)) {
                throw "fio JSON was not created: $OutFile"
            }
            if (-not (Test-Path -LiteralPath $TestFile)) {
                throw "Dedicated target file is missing after $Rw run ${Run}: $TestFile"
            }

            $Job = (Get-Content -Raw -LiteralPath $OutFile | ConvertFrom-Json).jobs[0]
            $IoSection = if ($ReadOnly) { $Job.read } else { $Job.write }
            if ($Job.error -ne 0) {
                throw "fio JSON reports error=$($Job.error) for $Rw run $Run"
            }
            if ($IoSection.io_bytes -le 0) {
                throw "$Rw run $Run did not record expected I/O."
            }

            if ($Run -lt $Runs -and $InterRunIdleSec -gt 0) {
                Write-Host "[idle] Waiting $InterRunIdleSec seconds before $Rw run $($Run + 1)"
                Start-Sleep -Seconds $InterRunIdleSec
            }
        }

        $RunnerManifest.completed_at = (Get-Date).ToString("o")
        $RunnerManifest.status = "complete"
        Save-Json -Value $RunnerManifest -Path $RunnerManifestPath

        Write-Host "[observer] Collecting post evidence for $Rw"
        Invoke-Observer `
            -RunLabel $RunLabel `
            -Workload $Workload `
            -Rw $Rw `
            -StatePhase $Phase.state_phase `
            -Phase "post"

        $Phase.status = "complete"
        $Phase.completed_at = (Get-Date).ToString("o")
        Save-ExperimentManifest
    }
    catch {
        $RunnerManifest.completed_at = (Get-Date).ToString("o")
        $RunnerManifest.status = "failed"
        Save-Json -Value $RunnerManifest -Path $RunnerManifestPath
        $Phase.status = "failed"
        $Phase.completed_at = (Get-Date).ToString("o")
        Save-ExperimentManifest
        throw
    }
}

Save-ExperimentManifest

Write-Host "=== External SSD matched mixed-workload controls ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Test file  : $TestFile"
Write-Host "Controls   : randread -> randwrite"
Write-Host "Runtime    : $RuntimeSec seconds x $Runs runs per control"
Write-Host "Start idle : $InitialIdleMinutes minutes"
Write-Host "Set idle   : $TransitionIdleMinutes minutes"
Write-Host "Run idle   : $InterRunIdleSec seconds"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    if ($InitialIdleMinutes -gt 0) {
        Write-Host "[idle] Waiting $InitialIdleMinutes minutes before the randread control"
        Start-Sleep -Seconds ($InitialIdleMinutes * 60)
    }

    Invoke-ControlSet -Phase $Phases[0] -Rw "randread"

    if ($TransitionIdleMinutes -gt 0) {
        Write-Host "[idle] Waiting $TransitionIdleMinutes minutes before the randwrite control"
        Start-Sleep -Seconds ($TransitionIdleMinutes * 60)
    }

    Invoke-ControlSet -Phase $Phases[1] -Rw "randwrite"

    $Manifest.completed_at = (Get-Date).ToString("o")
    $Manifest.status = "complete"
    Save-ExperimentManifest
}
catch {
    $Manifest.completed_at = (Get-Date).ToString("o")
    $Manifest.status = "failed"
    $Manifest.error = $_.Exception.Message
    Save-ExperimentManifest
    throw
}

Write-Host "=== Matched mixed-workload controls completed ==="
Write-Host "Read result : $(Join-Path $ResultRoot $ReadRunLabel)"
Write-Host "Write result: $(Join-Path $ResultRoot $WriteRunLabel)"
Write-Host "Manifest    : $ExperimentManifestPath"
