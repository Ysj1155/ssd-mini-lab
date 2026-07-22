# External SSD Execution Runbook

This is the fixed execution procedure for external SSD sustained runs.

Codex prepares and reviews the workflow but does not run fio unless explicitly asked. The user confirms the external SSD path and executes the traced runner locally.

## 1. Safety Boundary

- Use only the existing file target `E:\validation\ssd_lab_fio_testfile`.
- Do not use a raw physical-drive path or an internal OS-drive file.
- Keep each run under a unique `results/external_ssd/<run_id>/` directory.
- The traced runner refuses to overwrite a directory that already contains fio run JSON.
- Read workloads use fio's `--readonly` flag through the underlying runner.

Confirm the target before every run:

```powershell
cd D:\ssd_lab
Get-Item -LiteralPath "E:\validation\ssd_lab_fio_testfile" |
    Select-Object FullName, Length, LastWriteTime
Get-Volume -DriveLetter E
```

Stop if the file is missing, the drive letter changed, or the path does not begin with `E:\validation\`.

## 2. Next Experiment

The next run checks QD16 120s random-write reproducibility across sessions.

Run ID:

```text
sustained_rand_write_120s_qd16_trace_repeat3_20260722
```

Condition:

| Field | Value |
|---|---|
| rw | `randwrite` |
| block size | `4k` |
| queue depth | `16` |
| runtime | `120s` |
| test-file size | `512M` |
| direct | `1` |
| repeats | `3` |

This condition has already produced materially different results in two sessions. The new run determines whether the slower, higher-tail-latency session repeats when execution evidence is complete.

## 3. Fixed Execution Sequence

Run this single command from PowerShell or a PyCharm PowerShell terminal:

```powershell
cd D:\ssd_lab

powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_traced_sustained.ps1 `
  -RunLabel "sustained_rand_write_120s_qd16_trace_repeat3_20260722" `
  -Rw randwrite `
  -RuntimeSec 120 `
  -Iodepth 16 `
  -Runs 3 `
  -BlockSize 4k `
  -Size 512M `
  -TestFile "E:\validation\ssd_lab_fio_testfile"
```

The traced runner sets all environment variables in one process and executes:

```text
pre observer -> fio runner -> post observer
```

Before fio starts, confirm the printed values show `RuntimeSec: 120`, `Iodepth: 16`, and `Runs: 3`. Stop with `Ctrl+C` if they differ.

Evidence ownership remains separate:

| Producer | Responsibility | Expected artifact |
|---|---|---|
| Observer, pre | Read-only host/path/telemetry context before fio | `observer_manifest_pre.json` |
| Runner | fio execution, exit codes, raw JSON, time-series logs | `runner_manifest.json` and fio artifacts |
| Observer, post | Read-only host/path/telemetry context after fio | `observer_manifest_post.json` |

## 4. Post-Run Validation

```powershell
$runLabel = "sustained_rand_write_120s_qd16_trace_repeat3_20260722"
$runDir = Join-Path ".\results\external_ssd" $runLabel

Get-ChildItem -LiteralPath $runDir | Select-Object Name, Length, LastWriteTime
Select-String -Path (Join-Path $runDir "*_run*.json") `
  -Pattern '"error"|"filename"'
```

Expected minimum evidence:

- 3 fio run JSON files with `error: 0`
- fio bandwidth, IOPS, and latency logs for each run
- `runner_manifest.json`
- `observer_manifest_pre.json`
- `observer_manifest_post.json`
- JSON `filename` values resolving to `E:\validation\ssd_lab_fio_testfile`

Then rebuild derived evidence:

```powershell
python .\scripts\analysis\analyze_external_ssd_sustained.py
python .\scripts\analysis\build_external_ssd_run_manifest.py --result-set $runLabel
Get-Content -Raw (Join-Path $runDir "run_manifest.json")
```

The integrated run manifest may be `complete` even when telemetry is `limited`; collector limitations must remain explicit in the observer manifests.

## 5. Interpretation

Compare the new result against:

- `sustained_rand_write_120s_qd16_repeat3`
- `sustained_rand_write_120s_512M_4k_qd16_direct1_repeat3`

Review:

- average bandwidth and IOPS
- p99 and p99.9 completion latency
- run-to-run CV
- last-third IOPS / first-third IOPS
- last-third average completion latency / first-third average completion latency
- maximum-latency outliers
- observer and telemetry limitations

Do not infer internal FTL, GC, or USB root cause from these black-box file-target results.

## 6. Failure Handling

- Wrong or missing target path: stop before fio and correct the path.
- Existing fio JSON under the run ID: choose a new run ID; do not overwrite raw data.
- fio nonzero exit: preserve raw output and runner manifest; do not classify it as a successful result.
- Observer limitation: continue only if fio target safety is unaffected, then retain `limited` telemetry evidence.
- Missing logs or manifests: do not fabricate or backfill execution evidence.
