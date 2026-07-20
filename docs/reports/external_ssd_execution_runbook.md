# External SSD Execution Runbook

This runbook prepares fio execution for the external SSD DUT.

Codex should not run fio for this track unless explicitly asked. The user runs fio locally after confirming the target path.

## 1. Confirm DUT Path

Choose a test file path on the external SSD.

Example:

```powershell
$env:SSD_LAB_EXTERNAL_TESTFILE = "E:\validation\ssd_lab_fio_testfile"
```

This path is intentionally under `E:\validation` so the new product-validation run does not mix with older `E:\labs` experiments.

Do not use:

- raw physical drive paths
- the internal OS drive by accident
- ambiguous filenames such as `testfile` without a full path
- older folders such as `E:\labs\fio_test` or `E:\labs\ssd-mini-lab` for new product-validation output

## 2. Collect Environment Context

Run before fio:

```powershell
cd D:\ssd_lab
powershell -ExecutionPolicy Bypass -File .\scripts\collect_env_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\collect_storage_telemetry_windows.ps1
```

If `smartctl` is installed and a read-only scan is desired:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_SMARTCTL_SCAN = "1"
powershell -ExecutionPolicy Bypass -File .\scripts\collect_storage_telemetry_windows.ps1
```

## 3. Start with a Small Smoke Run

Use a small single run first to verify the target path.

Example fio command shape:

```powershell
fio --name=external_smoke `
  --filename="$env:SSD_LAB_EXTERNAL_TESTFILE" `
  --rw=randread `
  --bs=4k `
  --iodepth=1 `
  --size=512M `
  --runtime=30 `
  --time_based=1 `
  --direct=1 `
  --ioengine=windowsaio `
  --numjobs=1 `
  --group_reporting=1 `
  --output-format=json `
  --output=results\external_ssd\external_smoke.json
```

Check the JSON `filename` field after the smoke run. It must point to the external SSD path.

Expected path:

```text
E:\validation\ssd_lab_fio_testfile
```

## 4. Run Planned Test Cases

Use the matrix:

```text
configs/external_ssd_validation_matrix.yaml
```

Recommended first execution order:

1. `EXT-PERF-RR-QD-SWEEP`
2. `EXT-PERF-RW-QD-SWEEP`
3. `EXT-SUST-WRITE-120S`
4. `EXT-SUST-READ-120S`
5. `EXT-SUST-WRITE-300S`

Run the longer write test only after the smaller tests complete without path or space issues.

For the first product-validation pass, run the lightweight QD sweep smoke:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_EXTERNAL_TESTFILE = "E:\validation\ssd_lab_fio_testfile"
powershell -ExecutionPolicy Bypass -File .\scripts\runners\run_external_ssd_qd_smoke.ps1
```

Default smoke scope:

```text
randread/randwrite, 4k, QD 1/4/16/32, 512M, 30s, repeat=1
```


After the smoke pass is confirmed, run the same conditions with three repeats:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_EXTERNAL_TESTFILE = "E:\validation\ssd_lab_fio_testfile"
$env:SSD_LAB_EXTERNAL_LABEL = "qd_sweep_repeat3"
$env:SSD_LAB_EXTERNAL_REPEATS = "3"
$env:SSD_LAB_EXTERNAL_RUNTIME = "30"
$env:SSD_LAB_EXTERNAL_SIZE = "512M"
powershell -ExecutionPolicy Bypass -File .\scripts\runners\run_external_ssd_qd_smoke.ps1
```

Expected repeat output:

```text
results/external_ssd/qd_sweep_repeat3/
2 workloads x 4 QD x 3 repeats = 24 JSON files
```

For the next raw-data pass, run sustained random write at QD16:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_EXTERNAL_TESTFILE = "E:\validation\ssd_lab_fio_testfile"
$env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL = "sustained_rand_write_120s_qd16_repeat3"
$env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "rand_write"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RW = "randwrite"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = "120"
$env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "512M"
$env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "16"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = "3"
powershell -ExecutionPolicy Bypass -File .\scripts\runners\run_external_ssd_sustained.ps1
```

Expected sustained output:

```text
results/external_ssd/sustained_rand_write_120s_qd16_repeat3/
3 JSON files plus fio time-series logs
```

## 5. After fio

Collect:

- fio JSON outputs
- environment snapshot
- telemetry snapshot
- drive free-space state
- any observed temperature or device-status data

Then analyze:

```powershell
python .\scripts\analysis\parse_fio_results.py --input-dir results\external_ssd --output results\external_ssd_summary.csv
```

If the output layout differs, add a dedicated analyzer instead of forcing unrelated scripts to parse incompatible filenames.

## 6. Report

Use:

```text
docs/reports/external_ssd_product_validation.md
```

The report should include:

- DUT profile
- requirement matrix
- test matrix
- execution evidence
- p99 / p99.9 review
- sustained workload review
- telemetry observations
- anomaly review
- verdict
- limitations
