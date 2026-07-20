$ResultDir = "D:\ssd_lab\results"
$TargetFile = "E:\fio_testfile"
$Size = "2G"
$Repeats = 3

New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null

$tests = @(
    @{
        Name = "seq_read"
        Bs = "1M"
        Rw = "read"
        Iodepth = 32
    },
    @{
        Name = "seq_write"
        Bs = "1M"
        Rw = "write"
        Iodepth = 32
    },
    @{
        Name = "rand_read"
        Bs = "4k"
        Rw = "randread"
        Iodepth = 32
    },
    @{
        Name = "rand_write"
        Bs = "4k"
        Rw = "randwrite"
        Iodepth = 32
    }
)

foreach ($test in $tests) {
    for ($run = 1; $run -le $Repeats; $run++) {
        $outFile = Join-Path $ResultDir "$($test.Name)_run$run.json"

        Write-Host "Running $($test.Name) run $run ..."
        fio `
          --name=$($test.Name) `
          --filename=$TargetFile `
          --size=$Size `
          --bs=$($test.Bs) `
          --rw=$($test.Rw) `
          --iodepth=$($test.Iodepth) `
          --direct=1 `
          --thread=1 `
          --time_based=1 `
          --runtime=30 `
          --ramp_time=3 `
          --group_reporting `
          --output=$outFile `
          --output-format=json

        Start-Sleep -Seconds 3
    }
}