# run_sustained_smoke.ps1
#
# Purpose:
#   Run a conservative sustained fio smoke test.
#
# Safety:
#   This script uses a regular file path only.
#   It never targets raw block devices such as \\.\PhysicalDriveN.
#
# Default:
#   workload=rand_write
#   runtime=120s
#   size=1G
#   direct=1
#   repeats=1
#
# Usage:
#   cd D:\ssd_lab
#   .\run_sustained_smoke.ps1
#
# Optional overrides:
#   $env:SSD_LAB_SUSTAINED_RUNTIME = "300"
#   $env:SSD_LAB_SUSTAINED_SIZE = "2G"
#   $env:SSD_LAB_SUSTAINED_RUNS = "3"
#   $env:SSD_LAB_SUSTAINED_LABEL = "rand_write_300s_repeat3"

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\sustained_smoke"
$TestFile = Join-Path $BaseDir "fio_testfile_sustained_smoke"

$Runtime = if ($env:SSD_LAB_SUSTAINED_RUNTIME) { $env:SSD_LAB_SUSTAINED_RUNTIME } else { "120" }
$Size = if ($env:SSD_LAB_SUSTAINED_SIZE) { $env:SSD_LAB_SUSTAINED_SIZE } else { "1G" }
$Runs = if ($env:SSD_LAB_SUSTAINED_RUNS) { [int]$env:SSD_LAB_SUSTAINED_RUNS } else { 1 }
$Workload = if ($env:SSD_LAB_SUSTAINED_WORKLOAD) { $env:SSD_LAB_SUSTAINED_WORKLOAD } else { "rand_write" }
$Rw = if ($env:SSD_LAB_SUSTAINED_RW) { $env:SSD_LAB_SUSTAINED_RW } else { "randwrite" }
$Bs = if ($env:SSD_LAB_SUSTAINED_BS) { $env:SSD_LAB_SUSTAINED_BS } else { "4k" }
$Iodepth = if ($env:SSD_LAB_SUSTAINED_IODEPTH) { $env:SSD_LAB_SUSTAINED_IODEPTH } else { "16" }
$Direct = if ($env:SSD_LAB_SUSTAINED_DIRECT) { $env:SSD_LAB_SUSTAINED_DIRECT } else { "1" }
$LogAvgMsec = if ($env:SSD_LAB_SUSTAINED_LOG_AVG_MSEC) { $env:SSD_LAB_SUSTAINED_LOG_AVG_MSEC } else { "1000" }
$DefaultLabel = "${Workload}_${Runtime}s_${Size}_${Bs}_qd${Iodepth}_direct${Direct}"
$RunLabel = if ($env:SSD_LAB_SUSTAINED_LABEL) { $env:SSD_LAB_SUSTAINED_LABEL } else { $DefaultLabel }
$SafeLabel = $RunLabel -replace '[^A-Za-z0-9_.-]', '_'
$ResultDir = Join-Path $ResultRoot $SafeLabel

New-Item -ItemType Directory -Force $ResultDir | Out-Null

Write-Host "=== Sustained fio smoke test ==="
Write-Host "BaseDir     : $BaseDir"
Write-Host "ResultRoot  : $ResultRoot"
Write-Host "ResultDir   : $ResultDir"
Write-Host "Run label   : $SafeLabel"
Write-Host "TestFile    : $TestFile"
Write-Host "Workload    : $Workload"
Write-Host "rw          : $Rw"
Write-Host "bs          : $Bs"
Write-Host "iodepth     : $Iodepth"
Write-Host "size        : $Size"
Write-Host "runtime     : $Runtime"
Write-Host "direct      : $Direct"
Write-Host "runs        : $Runs"
Write-Host "log avg ms  : $LogAvgMsec"
Write-Host ""

for ($run = 1; $run -le $Runs; $run++) {
    $OutFile = Join-Path $ResultDir "${SafeLabel}_sustained_run${run}.json"
    $LogPrefix = Join-Path $ResultDir "${SafeLabel}_sustained_run${run}"

    Write-Host "Running sustained smoke: run=$run"
    Write-Host "Output: $OutFile"

    fio `
        --name="$Workload" `
        --filename="$TestFile" `
        --rw="$Rw" `
        --bs="$Bs" `
        --size="$Size" `
        --iodepth="$Iodepth" `
        --numjobs=1 `
        --direct="$Direct" `
        --thread=1 `
        --time_based `
        --runtime="$Runtime" `
        --group_reporting `
        --log_avg_msec="$LogAvgMsec" `
        --write_bw_log="$LogPrefix" `
        --write_iops_log="$LogPrefix" `
        --write_lat_log="$LogPrefix" `
        --output-format=json `
        --output="$OutFile"

    Write-Host "[OK] Done: $OutFile"
    Write-Host ""
}

Write-Host "[DONE] Sustained smoke test completed."
