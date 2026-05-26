# run_direct_buffered.ps1
#
# Purpose:
#   Run fio direct I/O vs buffered I/O comparison.
#
# Output:
#   results/direct_buffered/*.json
#
# Workloads:
#   rand_read, rand_write
#
# Fixed:
#   bs=4k
#   iodepth=16
#   size=2G
#   runtime=30s
#   numjobs=1
#
# Variable:
#   direct=1 vs direct=0

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$ResultDir = Join-Path $BaseDir "results\direct_buffered"
$TestFile = Join-Path $BaseDir "fio_testfile_direct_buffered"

New-Item -ItemType Directory -Force $ResultDir | Out-Null

Write-Host "=== Direct vs Buffered I/O fio run ==="
Write-Host "BaseDir   : $BaseDir"
Write-Host "ResultDir : $ResultDir"
Write-Host "TestFile  : $TestFile"

# ------------------------------------------------------------
# Prefill test file
# ------------------------------------------------------------
# Read workloads need an existing test file.
# This prefill creates a 2G file using direct I/O.
Write-Host ""
Write-Host "=== Prefill test file ==="

fio `
  --name=prefill `
  --filename="$TestFile" `
  --rw=write `
  --bs=1M `
  --size=2G `
  --iodepth=1 `
  --numjobs=1 `
  --direct=1 `
  --thread=1 `
  --output-format=json `
  --output="$ResultDir\prefill.json"

Write-Host "[OK] Prefill completed"

# ------------------------------------------------------------
# Main experiment
# ------------------------------------------------------------

$Workloads = @(
    @{ Name = "rand_read";  Rw = "randread"  },
    @{ Name = "rand_write"; Rw = "randwrite" }
)

$DirectModes = @(1, 0)
$Runs = @(1, 2, 3)

foreach ($workload in $Workloads) {
    foreach ($direct in $DirectModes) {
        foreach ($run in $Runs) {
            $name = $workload.Name
            $rw = $workload.Rw
            $outFile = "$ResultDir\${name}_direct${direct}_run${run}.json"

            Write-Host ""
            Write-Host "Running: workload=$name direct=$direct run=$run"
            Write-Host "Output : $outFile"

            fio `
                --name=$name `
                --filename="$TestFile" `
                --rw=$rw `
                --bs=4k `
                --size=2G `
                --iodepth=16 `
                --numjobs=1 `
                --direct=$direct `
                --thread=1 `
                --time_based `
                --runtime=30 `
                --group_reporting `
                --output-format=json `
                --output="$outFile"

            Write-Host "[OK] Done: $outFile"
        }
    }
}

Write-Host ""
Write-Host "[DONE] Direct vs buffered fio runs completed."