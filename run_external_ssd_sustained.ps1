# run_external_ssd_sustained.ps1
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
# Default:
#   workload=rand_write
#   runtime=120s
#   size=512M
#   iodepth=16
#   repeats=3

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
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
$ReadOnly = $Rw -match "read"

$DefaultLabel = "sustained_${Workload}_${Runtime}s_${Size}_${Bs}_qd${Iodepth}_direct${Direct}_repeat${Runs}"
$RunLabel = if ($env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL) { $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL } else { $DefaultLabel }
$SafeLabel = $RunLabel -replace '[^A-Za-z0-9_.-]', '_'
$ResultDir = Join-Path $ResultRoot $SafeLabel

New-Item -ItemType Directory -Force $ResultDir | Out-Null

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
Write-Host ""

if (-not ($TestFile -like "E:\validation\*")) {
    Write-Host "[ERROR] TestFile must stay under E:\validation for this track."
    Write-Host "Current TestFile: $TestFile"
    exit 1
}

if (-not (Test-Path -LiteralPath $TestFile)) {
    Write-Host "[ERROR] Test file does not exist: $TestFile"
    Write-Host "Create it first, for example:"
    Write-Host "  fsutil file createnew E:\validation\ssd_lab_fio_testfile 536870912"
    exit 1
}

$fioCommand = Get-Command fio -ErrorAction SilentlyContinue
if ($null -eq $fioCommand) {
    Write-Host "[ERROR] fio command not found. Check PATH."
    exit 1
}

Write-Host "fio found   : $($fioCommand.Source)"
Write-Host ""

for ($Run = 1; $Run -le $Runs; $Run++) {
    $OutFile = Join-Path $ResultDir "${SafeLabel}_run${Run}.json"
    $LogPrefix = Join-Path $ResultDir "${SafeLabel}_run${Run}"

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
        Write-Host "[ERROR] fio failed."
        Write-Host "Run      : $Run"
        Write-Host "Workload : $Workload"
        exit $LASTEXITCODE
    }

    Write-Host "[OK] Saved: $OutFile"
    Write-Host ""
}

Write-Host "=== External SSD sustained run completed ==="
Write-Host "Expected JSON files: $Runs"
Write-Host "Actual JSON files  : $((Get-ChildItem -Path $ResultDir -Filter *.json).Count)"
Write-Host "Result directory   : $ResultDir"