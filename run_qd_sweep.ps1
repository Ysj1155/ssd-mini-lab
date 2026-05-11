# run_qd_sweep.ps1
#
# Purpose:
#   Run fio QD sweep for SSD mini-lab.
#
# Workloads:
#   - rand_read
#   - rand_write
#
# Queue depths:
#   - 1, 4, 16, 32
#
# Repeats:
#   - 3
#
# Output:
#   D:\ssd_lab\results\qd_sweep\*.json
#
# Notes:
#   Check $TestFile before running.
#   It should point to the external SSD drive, not the internal D: drive.

$ErrorActionPreference = "Stop"

# =========================
# User-configurable settings
# =========================

$BaseDir = "D:\ssd_lab"
$ResultDir = Join-Path $BaseDir "results\qd_sweep"

# IMPORTANT:
# Change this if your external SSD drive letter is not E:
# Example:
#   E:\fio_testfile_qd
#   F:\fio_testfile_qd
$TestFile = "E:\fio_testfile_qd"

$Size = "2G"
$Runtime = 30
$RampTime = 3
$Repeats = 3

$BlockSize = "4k"
$QueueDepths = @(1, 4, 16, 32)

$Workloads = @(
    @{
        Name = "rand_read"
        Rw   = "randread"
    },
    @{
        Name = "rand_write"
        Rw   = "randwrite"
    }
)

# =========================
# Prepare output directory
# =========================

New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null

Write-Host ""
Write-Host "=== SSD Mini-Lab QD Sweep ==="
Write-Host "BaseDir    : $BaseDir"
Write-Host "ResultDir  : $ResultDir"
Write-Host "TestFile   : $TestFile"
Write-Host "BlockSize  : $BlockSize"
Write-Host "QD list    : $($QueueDepths -join ', ')"
Write-Host "Repeats    : $Repeats"
Write-Host ""

# =========================
# Safety check
# =========================

$TestDrive = Split-Path $TestFile -Qualifier

if (-not (Test-Path $TestDrive)) {
    Write-Host "[ERROR] Test drive does not exist: $TestDrive"
    Write-Host "Check your external SSD drive letter."
    exit 1
}

if ($TestFile -like "D:\*") {
    Write-Host "[WARNING] TestFile is under D: drive."
    Write-Host "If D: is not your external SSD, stop now and edit `$TestFile."
    Write-Host "Current TestFile: $TestFile"
    pause
}

# =========================
# fio existence check
# =========================

$fioCommand = Get-Command fio -ErrorAction SilentlyContinue

if ($null -eq $fioCommand) {
    Write-Host "[ERROR] fio command not found."
    Write-Host "Check whether fio is installed and added to PATH."
    exit 1
}

Write-Host "fio found   : $($fioCommand.Source)"
Write-Host ""

# =========================
# Run QD sweep
# =========================

foreach ($workload in $Workloads) {
    $WorkloadName = $workload.Name
    $RwMode = $workload.Rw

    foreach ($QD in $QueueDepths) {
        for ($Run = 1; $Run -le $Repeats; $Run++) {

            $OutputFile = Join-Path $ResultDir "$($WorkloadName)_qd$($QD)_run$($Run).json"

            Write-Host "----------------------------------------"
            Write-Host "Workload : $WorkloadName"
            Write-Host "rw       : $RwMode"
            Write-Host "bs       : $BlockSize"
            Write-Host "iodepth  : $QD"
            Write-Host "run      : $Run / $Repeats"
            Write-Host "output   : $OutputFile"
            Write-Host "----------------------------------------"

            fio `
                --name="$WorkloadName" `
                --filename="$TestFile" `
                --rw="$RwMode" `
                --bs="$BlockSize" `
                --iodepth="$QD" `
                --size="$Size" `
                --direct=1 `
                --thread=1 `
                --time_based=1 `
                --runtime="$Runtime" `
                --ramp_time="$RampTime" `
                --group_reporting `
                --output-format=json `
                --output="$OutputFile"

            if ($LASTEXITCODE -ne 0) {
                Write-Host "[ERROR] fio failed."
                Write-Host "Workload : $WorkloadName"
                Write-Host "QD       : $QD"
                Write-Host "Run      : $Run"
                exit $LASTEXITCODE
            }

            Write-Host "[OK] Saved: $OutputFile"
            Write-Host ""
        }
    }
}

Write-Host ""
Write-Host "=== QD sweep completed ==="
Write-Host "Expected JSON files: $($Workloads.Count * $QueueDepths.Count * $Repeats)"
Write-Host "Actual JSON files  : $((Get-ChildItem $ResultDir -Filter *.json).Count)"
Write-Host "Result directory   : $ResultDir"