# scripts/runners/run_external_ssd_sustained.ps1
#
# Purpose:
#   Run external-SSD sustained fio raw-data collection.
#
# Scope:
#   Black-box external SSD validation track.
#   Target file must stay under E:\validation.
#
# Safety:
#   This script never targets raw physical drives.
#   It refuses to run unless the test file already exists under E:\validation.
#   Read workloads use fio's readonly flag.
#
# Runner evidence:
#   Writes runner_manifest.json beside fio JSON/log artifacts.
#
# Default:
#   workload=rand_write
#   runtime=120s
#   size=512M
#   iodepth=16
#   repeats=3

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$SafetyModule = Join-Path $BaseDir "scripts\lib\ExternalSsdSafety.psm1"
$DutIdentityConfig = Join-Path $BaseDir "configs\external_ssd_dut_identity.json"
Import-Module $SafetyModule -Force
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$TestFile = if ($env:SSD_LAB_EXTERNAL_TESTFILE) { $env:SSD_LAB_EXTERNAL_TESTFILE } else { "E:\validation\ssd_lab_fio_testfile" }

$Runtime = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME) { $env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME } else { "120" }
$Size = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE) { $env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE } else { "512M" }
$Runs = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS) { [int]$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS } else { 3 }
$Workload = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD) { $env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD } else { "rand_write" }
$Rw = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_RW) { $env:SSD_LAB_EXTERNAL_SUSTAINED_RW } else { "randwrite" }
$Bs = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_BS) { $env:SSD_LAB_EXTERNAL_SUSTAINED_BS } else { "4k" }
$Iodepth = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH) { $env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH } else { "16" }
$Direct = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT) { $env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT } else { "1" }
$LogAvgMsec = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_LOG_AVG_MSEC) { $env:SSD_LAB_EXTERNAL_SUSTAINED_LOG_AVG_MSEC } else { "1000" }
$TestCaseId = if ($env:SSD_LAB_EXTERNAL_TEST_CASE_ID) { $env:SSD_LAB_EXTERNAL_TEST_CASE_ID } else { $null }
$ExperimentId = if ($env:SSD_LAB_EXTERNAL_EXPERIMENT_ID) { $env:SSD_LAB_EXTERNAL_EXPERIMENT_ID } else { $null }
$StatePhase = if ($env:SSD_LAB_EXTERNAL_STATE_PHASE) { $env:SSD_LAB_EXTERNAL_STATE_PHASE } else { $null }
$ReadOnly = $Rw -match "read"

$DefaultLabel = "sustained_${Workload}_${Runtime}s_${Size}_${Bs}_qd${Iodepth}_direct${Direct}_repeat${Runs}"
$RunLabel = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL) { $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL } else { $DefaultLabel }
$SafeLabel = $RunLabel -replace '[^A-Za-z0-9_.-]', '_'
$ResultDir = Join-Path $ResultRoot $SafeLabel
$RunnerManifestPath = Join-Path $ResultDir "runner_manifest.json"

function Save-RunnerManifest {
    param(
        [object]$Manifest,
        [string]$Path
    )

    $Manifest |
        ConvertTo-Json -Depth 8 |
        Out-File -FilePath $Path -Encoding utf8
}

Write-Host "=== External SSD sustained raw-data run ==="
Write-Host "BaseDir     : $BaseDir"
Write-Host "ResultRoot  : $ResultRoot"
Write-Host "Run label   : $SafeLabel"
Write-Host "ResultDir   : $ResultDir"
Write-Host "TestFile    : $TestFile"
Write-Host "Workload    : $Workload"
Write-Host "rw          : $Rw"
Write-Host "bs          : $Bs"
Write-Host "iodepth     : $Iodepth"
Write-Host "size        : $Size"
Write-Host "runtime     : $Runtime"
Write-Host "direct      : $Direct"
Write-Host "runs        : $Runs"
Write-Host "readonly    : $ReadOnly"
Write-Host "log avg ms  : $LogAvgMsec"
Write-Host "test case   : $TestCaseId"
Write-Host "experiment  : $ExperimentId"
Write-Host "state phase : $StatePhase"
Write-Host ""

$DutPreflight = Assert-ExternalSsdTarget `
    -TestFile $TestFile `
    -IdentityConfigPath $DutIdentityConfig `
    -RequireExistingTarget
$TestFile = $DutPreflight.canonical_target
New-Item -ItemType Directory -Force $ResultDir | Out-Null

$fioCommand = Get-Command fio -ErrorAction SilentlyContinue
if ($null -eq $fioCommand) {
    Write-Host "[ERROR] fio command not found. Check PATH."
    exit 1
}

Write-Host "fio found   : $($fioCommand.Source)"
Write-Host ""

$RunnerManifest = [ordered]@{
    schema_version = "1.0"
    role = "runner"
    run_id = $SafeLabel
    test_case_id = $TestCaseId
    experiment_id = $ExperimentId
    state_phase = $StatePhase
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    runner = "scripts/runners/run_external_ssd_sustained.ps1"
    safety = "canonical file-target runner on the enrolled DUT; no raw physical-drive target"
    dut_preflight = $DutPreflight
    fio_command = $fioCommand.Source
    result_dir = $ResultDir
    test_file = $TestFile
    conditions = [ordered]@{
        workload = $Workload
        rw = $Rw
        bs = $Bs
        iodepth = $Iodepth
        size = $Size
        runtime_sec = $Runtime
        direct = $Direct
        numjobs = "1"
        log_avg_msec = $LogAvgMsec
        readonly = $ReadOnly
        planned_runs = $Runs
    }
    runs = @()
}

Save-RunnerManifest -Manifest $RunnerManifest -Path $RunnerManifestPath

for ($Run = 1; $Run -le $Runs; $Run++) {
    $OutFile = Join-Path $ResultDir "${SafeLabel}_run${Run}.json"
    $LogPrefix = Join-Path $ResultDir "${SafeLabel}_run${Run}"
    $RunRecord = [ordered]@{
        run = $Run
        started_at = (Get-Date).ToString("o")
        completed_at = $null
        status = "started"
        exit_code = $null
        fio_json = $OutFile
        log_prefix = $LogPrefix
    }

    Write-Host "----------------------------------------"
    Write-Host "Running sustained: run=$Run / $Runs"
    Write-Host "Output: $OutFile"
    Write-Host "----------------------------------------"

    $fioArgs = @(
        "--name=$Workload",
        "--filename=$TestFile",
        "--rw=$Rw",
        "--bs=$Bs",
        "--size=$Size",
        "--iodepth=$Iodepth",
        "--numjobs=1",
        "--direct=$Direct",
        "--thread=1",
        "--unlink=0",
        "--time_based=1",
        "--runtime=$Runtime",
        "--group_reporting=1",
        "--log_avg_msec=$LogAvgMsec",
        "--write_bw_log=$LogPrefix",
        "--write_iops_log=$LogPrefix",
        "--write_lat_log=$LogPrefix",
        "--output-format=json",
        "--output=$OutFile"
    )

    if ($ReadOnly) {
        $fioArgs += "--readonly"
    }

    & fio @fioArgs

    if ($LASTEXITCODE -ne 0) {
        $RunRecord.completed_at = (Get-Date).ToString("o")
        $RunRecord.status = "failed"
        $RunRecord.exit_code = $LASTEXITCODE
        $RunnerManifest.runs += $RunRecord
        $RunnerManifest.completed_at = (Get-Date).ToString("o")
        $RunnerManifest.status = "failed"
        Save-RunnerManifest -Manifest $RunnerManifest -Path $RunnerManifestPath

        Write-Host "[ERROR] fio failed."
        Write-Host "Run      : $Run"
        Write-Host "Workload : $Workload"
        exit $LASTEXITCODE
    }

    $RunRecord.completed_at = (Get-Date).ToString("o")
    $RunRecord.status = "complete"
    $RunRecord.exit_code = 0
    $RunnerManifest.runs += $RunRecord
    Save-RunnerManifest -Manifest $RunnerManifest -Path $RunnerManifestPath

    Write-Host "[OK] Saved: $OutFile"
    Write-Host ""
}

$RunnerManifest.completed_at = (Get-Date).ToString("o")
$RunnerManifest.status = "complete"
Save-RunnerManifest -Manifest $RunnerManifest -Path $RunnerManifestPath

Write-Host "=== External SSD sustained run completed ==="
Write-Host "Expected JSON files: $Runs"
Write-Host "Actual fio JSON files: $((Get-ChildItem -Path $ResultDir -Filter '*_run*.json').Count)"
Write-Host "Result directory   : $ResultDir"
Write-Host "Runner manifest    : $RunnerManifestPath"
