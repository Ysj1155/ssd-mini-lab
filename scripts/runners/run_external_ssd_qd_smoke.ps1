# scripts/runners/run_external_ssd_qd_smoke.ps1
#
# Purpose:
#   Run a lightweight external-SSD QD sweep smoke test.
#
# Scope:
#   This is for the black-box external SSD validation track.
#   It uses the existing file target at E:\validation\ssd_lab_fio_testfile.
#
# Safety:
#   This script never targets a raw physical drive.
#   It refuses to run unless the test file already exists under E:\validation.
#   Read workloads use fio's readonly flag.

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$SafetyModule = Join-Path $BaseDir "scripts\lib\ExternalSsdSafety.psm1"
$DutIdentityConfig = Join-Path $BaseDir "configs\external_ssd_dut_identity.json"
Import-Module $SafetyModule -Force
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$RunLabel = if ($env:SSD_LAB_EXTERNAL_LABEL) { $env:SSD_LAB_EXTERNAL_LABEL } else { "qd_sweep_smoke" }
$SafeLabel = $RunLabel -replace '[^A-Za-z0-9_.-]', '_'
$ResultDir = Join-Path $ResultRoot $SafeLabel
$TestFile = if ($env:SSD_LAB_EXTERNAL_TESTFILE) {
    $env:SSD_LAB_EXTERNAL_TESTFILE
}
else {
    "E:\validation\ssd_lab_fio_testfile"
}

$Size = if ($env:SSD_LAB_EXTERNAL_SIZE) { $env:SSD_LAB_EXTERNAL_SIZE } else { "512M" }
$Runtime = if ($env:SSD_LAB_EXTERNAL_RUNTIME) { $env:SSD_LAB_EXTERNAL_RUNTIME } else { "30" }
$Repeats = if ($env:SSD_LAB_EXTERNAL_REPEATS) { [int]$env:SSD_LAB_EXTERNAL_REPEATS } else { 1 }
$BlockSize = "4k"
$QueueDepths = @(1, 4, 16, 32)

$Workloads = @(
    @{
        Name = "rand_read"
        Rw = "randread"
        ReadOnly = $true
    },
    @{
        Name = "rand_write"
        Rw = "randwrite"
        ReadOnly = $false
    }
)

Write-Host "=== External SSD QD sweep smoke ==="
Write-Host "BaseDir    : $BaseDir"
Write-Host "ResultRoot : $ResultRoot"
Write-Host "Run label  : $SafeLabel"
Write-Host "ResultDir  : $ResultDir"
Write-Host "TestFile   : $TestFile"
Write-Host "Size       : $Size"
Write-Host "Runtime    : $Runtime"
Write-Host "Repeats    : $Repeats"
Write-Host "QD list    : $($QueueDepths -join ', ')"
Write-Host ""

$DutPreflight = Assert-ExternalSsdTarget `
    -TestFile $TestFile `
    -IdentityConfigPath $DutIdentityConfig `
    -RequireExistingTarget
$TestFile = $DutPreflight.canonical_target
New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null

$fioCommand = Get-Command fio -ErrorAction SilentlyContinue
if ($null -eq $fioCommand) {
    Write-Host "[ERROR] fio command not found. Check PATH."
    exit 1
}

Write-Host "fio found  : $($fioCommand.Source)"
Write-Host ""

foreach ($workload in $Workloads) {
    foreach ($QD in $QueueDepths) {
        for ($Run = 1; $Run -le $Repeats; $Run++) {
            $OutputFile = Join-Path $ResultDir "$($workload.Name)_qd$($QD)_run$($Run).json"

            Write-Host "----------------------------------------"
            Write-Host "Workload : $($workload.Name)"
            Write-Host "rw       : $($workload.Rw)"
            Write-Host "bs       : $BlockSize"
            Write-Host "iodepth  : $QD"
            Write-Host "run      : $Run / $Repeats"
            Write-Host "output   : $OutputFile"
            Write-Host "readonly : $($workload.ReadOnly)"
            Write-Host "----------------------------------------"

            $fioArgs = @(
                "--name=$($workload.Name)",
                "--filename=$TestFile",
                "--rw=$($workload.Rw)",
                "--bs=$BlockSize",
                "--iodepth=$QD",
                "--size=$Size",
                "--runtime=$Runtime",
                "--time_based=1",
                "--direct=1",
                "--ioengine=windowsaio",
                "--thread=1",
                "--unlink=0",
                "--numjobs=1",
                "--group_reporting=1",
                "--output-format=json",
                "--output=$OutputFile"
            )

            if ($workload.ReadOnly) {
                $fioArgs += "--readonly"
            }

            & fio @fioArgs

            if ($LASTEXITCODE -ne 0) {
                Write-Host "[ERROR] fio failed."
                Write-Host "Workload : $($workload.Name)"
                Write-Host "QD       : $QD"
                Write-Host "Run      : $Run"
                exit $LASTEXITCODE
            }

            Write-Host "[OK] Saved: $OutputFile"
            Write-Host ""
        }
    }
}

Write-Host "=== External SSD QD sweep smoke completed ==="
Write-Host "Expected JSON files: $($Workloads.Count * $QueueDepths.Count * $Repeats)"
Write-Host "Actual JSON files  : $((Get-ChildItem -Path $ResultDir -Filter *.json).Count)"
Write-Host "Result directory   : $ResultDir"