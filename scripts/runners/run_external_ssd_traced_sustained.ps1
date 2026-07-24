# scripts/runners/run_external_ssd_traced_sustained.ps1
#
# Purpose:
#   Execute one external SSD sustained run with pre/post observer evidence.
#
# The user runs this script locally. It keeps all fio conditions in the same
# PowerShell process so environment variables cannot be lost between steps.

param(
    [Parameter(Mandatory = $true)]
    [string]$RunLabel,

    [ValidateSet("randread", "randwrite")]
    [string]$Rw = "randwrite",

    [ValidateRange(1, 86400)]
    [int]$RuntimeSec = 120,

    [ValidateRange(1, 1024)]
    [int]$Iodepth = 16,

    [ValidateRange(1, 100)]
    [int]$Runs = 3,

    [string]$BlockSize = "4k",
    [string]$Size = "512M",
    [string]$TestFile = "E:\validation\ssd_lab_fio_testfile",
    [string]$TestCaseId = "",
    [string]$ExperimentId = "",
    [string]$StatePhase = ""
)

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$SafeLabel = $RunLabel -replace '[^A-Za-z0-9_.-]', '_'
$ResultDir = Join-Path $ResultRoot $SafeLabel
$Workload = if ($Rw -eq "randread") { "rand_read" } else { "rand_write" }

if (-not ($TestFile -like "E:\validation\*")) {
    throw "TestFile must stay under E:\validation. Current: $TestFile"
}

if (-not (Test-Path -LiteralPath $TestFile)) {
    throw "Test file does not exist: $TestFile"
}

if (Test-Path -LiteralPath $ResultDir) {
    $existingRuns = @(Get-ChildItem -LiteralPath $ResultDir -Filter "*_run*.json" -ErrorAction SilentlyContinue)
    if ($existingRuns.Count -gt 0) {
        throw "Result directory already contains fio JSON. Use a new RunLabel: $ResultDir"
    }
}

$env:SSD_LAB_EXTERNAL_TESTFILE = $TestFile
$env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL = $SafeLabel
$env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = $Workload
$env:SSD_LAB_EXTERNAL_SUSTAINED_RW = $Rw
$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = $RuntimeSec.ToString()
$env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = $Size
$env:SSD_LAB_EXTERNAL_SUSTAINED_BS = $BlockSize
$env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = $Iodepth.ToString()
$env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = $Runs.ToString()
$env:SSD_LAB_EXTERNAL_TEST_CASE_ID = $TestCaseId
$env:SSD_LAB_EXTERNAL_EXPERIMENT_ID = $ExperimentId
$env:SSD_LAB_EXTERNAL_STATE_PHASE = $StatePhase

$Conditions = [ordered]@{
    TestFile = $TestFile
    RunLabel = $SafeLabel
    Workload = $Rw
    RuntimeSec = $RuntimeSec
    Size = $Size
    BlockSize = $BlockSize
    Iodepth = $Iodepth
    Direct = 1
    Runs = $Runs
    TestCaseId = $TestCaseId
    ExperimentId = $ExperimentId
    StatePhase = $StatePhase
}

Write-Host "=== Traced external SSD sustained run ==="
[pscustomobject]$Conditions | Format-List | Out-Host

$ObserverScript = Join-Path $BaseDir "scripts\observers\collect_external_ssd_observer.ps1"
$RunnerScript = Join-Path $BaseDir "scripts\runners\run_external_ssd_sustained.ps1"

Write-Host "[1/3] Collecting pre observer evidence"
powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $SafeLabel -Phase pre
if ($LASTEXITCODE -ne 0) {
    throw "Pre observer process failed with exit code $LASTEXITCODE"
}

Write-Host "[2/3] Running fio"
powershell -ExecutionPolicy Bypass -File $RunnerScript
if ($LASTEXITCODE -ne 0) {
    throw "fio runner failed with exit code $LASTEXITCODE"
}

Write-Host "[3/3] Collecting post observer evidence"
powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $SafeLabel -Phase post
if ($LASTEXITCODE -ne 0) {
    throw "Post observer process failed with exit code $LASTEXITCODE"
}

Write-Host "=== Traced run completed ==="
Write-Host "Result directory: $ResultDir"
Write-Host "Next: analyze results and build the integrated run manifest."
