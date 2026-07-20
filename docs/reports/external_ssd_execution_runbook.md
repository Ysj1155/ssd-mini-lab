# External SSD Execution Runbook

This is the fixed execution procedure for the next external SSD sustained run.

Codex prepares and reviews the workflow but does not run fio unless explicitly asked. The user confirms the external SSD path and executes fio locally.

## 1. Safety Boundary

- Use only the existing file target `E:\validation\ssd_lab_fio_testfile`.
- Do not use a raw physical-drive path.
- Do not substitute an internal OS-drive file.
- Keep new product-validation runs under `results/external_ssd/<run_id>/`.
- Read workloads use fio's `--readonly` flag through the runner.

Confirm the target before every run:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_EXTERNAL_TESTFILE = "E:\validation\ssd_lab_fio_testfile"
Get-Item -LiteralPath $env:SSD_LAB_EXTERNAL_TESTFILE | Select-Object FullName, Length, LastWriteTime
Get-Volume -DriveLetter E
```

Stop if the file is missing, the drive letter changed, or the path does not begin with `E:\validation\`.

## 2. Define One Run ID and Its Conditions

Set every condition explicitly in the same PowerShell session. For the next evidence-complete confirmation run:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_EXTERNAL_TESTFILE = "E:\validation\ssd_lab_fio_testfile"
$env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL = "sustained_rand_write_300s_qd32_trace_repeat3"
$env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "rand_write"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RW = "randwrite"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = "300"
$env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "512M"
$env:SSD_LAB_EXTERNAL_SUSTAINED_BS = "4k"
$env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "32"
$env:SSD_LAB_EXTERNAL_SUSTAINED_DIRECT = "1"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = "3"
```

This repeats the current QoS risk candidate under the new evidence model. The distinct run ID preserves the earlier result set and allows a cross-session confirmation without overwriting raw data.

## 3. Fixed Execution Sequence

Run these commands in order:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\observers\collect_external_ssd_observer.ps1 -Phase pre
powershell -ExecutionPolicy Bypass -File .\scripts\runners\run_external_ssd_sustained.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\observers\collect_external_ssd_observer.ps1 -Phase post
```

Evidence ownership is intentionally separated:

| Producer | Responsibility | Expected artifact |
|---|---|---|
| Observer, pre | Read-only host/path/telemetry context before fio | `observer_manifest_pre.json` |
| Runner | fio execution, exit codes, raw JSON, time-series logs | `runner_manifest.json` and fio artifacts |
| Observer, post | Read-only host/path/telemetry context after fio | `observer_manifest_post.json` |

All three manifests must share the same run ID from `SSD_LAB_EXTERNAL_SUSTAINED_LABEL`.

## 4. Post-Run Validation

First verify file count, fio status, and target path:

```powershell
$runDir = Join-Path ".\results\external_ssd" $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL
Get-ChildItem -LiteralPath $runDir | Select-Object Name, Length, LastWriteTime
Select-String -Path (Join-Path $runDir "*_run*.json") -Pattern '"error"|"filename"'
```

Expected minimum evidence:

- 3 fio run JSON files with `error: 0`
- fio time-series logs for each run
- `runner_manifest.json`
- `observer_manifest_pre.json`
- `observer_manifest_post.json`
- JSON `filename` values resolving to `E:\validation\ssd_lab_fio_testfile`

Then rebuild the derived evidence:

```powershell
python .\scripts\analysis\analyze_external_ssd_sustained.py
python .\scripts\analysis\build_external_ssd_run_manifest.py --result-set $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL
```

Inspect the integrated manifest:

```powershell
Get-Content -Raw (Join-Path $runDir "run_manifest.json")
```

The expected integrated status is `complete`. A `limited` status is acceptable only when its anomaly list explicitly identifies the missing or restricted evidence.

## 5. Interpretation and Reporting

Review these outputs before changing the report:

- `results/external_ssd_sustained_summary.csv`
- `results/external_ssd_sustained_repeatability.csv`
- `results/external_ssd_sustained_window_summary.csv`
- `results/external_ssd/<run_id>/run_manifest.json`

Compare the confirmation run against `sustained_rand_write_300s_qd32_repeat3` using:

- average bandwidth and IOPS
- p99 and p99.9 completion latency
- run-to-run CV
- last-third IOPS / first-third IOPS
- last-third average completion latency / first-third average completion latency
- observer limitations and available telemetry

Do not infer internal FTL or GC behavior from these black-box file-target results.

## 6. Failure Handling

- Wrong or missing target path: stop before fio and correct the path.
- fio nonzero exit: preserve the raw output and runner manifest; do not merge it into a successful result.
- Observer limitation: continue only if fio safety is unaffected, then retain the explicit `limited` status.
- Missing logs or manifests: do not fabricate or backfill execution evidence; rerun with a new run ID if complete traceability is required.
