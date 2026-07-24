# External SSD Execution Runbook

Codex prepares and reviews external SSD workflows but does not run fio unless explicitly asked. The user confirms the target and executes the prepared PowerShell runner locally.

## 1. Completed Checkpoint

`EXT-STATE-REPRO-002` completed three separately initiated paired sessions. Its bandwidth deltas were -6.37%, -7.59%, and +23.33%, so the conditioning-uplift direction was not reproduced.

The state study is closed. Do not add sessions merely to search for a preferred direction.

## 2. Next Experiment

Test protocol: `EXT-LARGE-WS-SEQ-001`

Question:

> Does sequential throughput remain stable while completing one 32 GiB write and one 32 GiB read?

Fixed sequence:

```text
same physical USB port
  -> verify E: health and at least 40 GiB free
  -> confirm dedicated target does not exist
  -> 5-minute idle
  -> 32 GiB sequential write, bs=1M, QD4, direct=1, run=1
  -> verify exact 32 GiB file length
  -> 60-second idle
  -> 32 GiB sequential readonly read, bs=1M, QD4, direct=1, run=1
```

Both fio phases are completion-based. They do not use `time_based` or repeatedly wrap a small file.

## 3. Safety Boundary

This experiment creates and writes exactly one dedicated file:

```text
E:\validation\ssd_lab_seq_32g
```

The runner:

- refuses paths outside `E:\validation\`
- refuses an existing target file
- refuses less than 40 GiB free space
- requires E: volume `Healthy / OK`
- requires explicit same-port and dedicated-write confirmations
- never targets a raw physical drive
- retains the 32 GiB file after completion

The write amount is 32 GiB. The read phase does not modify the file. Do not delete the file until the result has been reviewed and any desired follow-up read or verification work is complete.

## 4. Preflight

Use an Administrator PowerShell or a PyCharm PowerShell terminal with equivalent storage-query access.

```powershell
cd D:\ssd_lab

Get-Volume -DriveLetter E |
  Select-Object DriveLetter, FriendlyName, FileSystemType, HealthStatus, OperationalStatus, SizeRemaining, Size

Test-Path -LiteralPath "E:\validation\ssd_lab_seq_32g"
Get-ChildItem -LiteralPath "E:\validation"
```

Expected:

- E: is the intended external SSD
- `HealthStatus` is `Healthy`
- `OperationalStatus` contains `OK`
- free space is greater than 40 GiB
- `Test-Path` returns `False`

Stop if any condition differs. Do not remove or overwrite an existing file through the runner.

## 5. Fixed Execution Command

```powershell
cd D:\ssd_lab

powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_large_ws_seq.ps1 `
  -ExperimentLabel "large_ws_seq_32g_20260724" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -InitialIdleMinutes 5 `
  -ReadIdleSec 60 `
  -ConfirmSamePort `
  -ConfirmDedicatedFileWrite
```

The runner prints the target, available space, sequence, and parent manifest before waiting. Stop with `Ctrl+C` if they are not the intended values.

Expected result IDs:

```text
sustained_large_ws_seq_32g_20260724_seqwrite_32g_run1
sustained_large_ws_seq_32g_20260724_seqread_32g_run1
```

Parent manifest:

```text
results/external_ssd/_experiments/large_ws_seq_32g_20260724/experiment_manifest.json
```

## 6. Expected Evidence

Each write/read result directory must contain:

- one fio JSON with `error: 0`
- 1-second bandwidth, IOPS, and latency logs
- `runner_manifest.json`
- `observer_manifest_pre.json`
- `observer_manifest_post.json`
- the intended E: filename and 32G size in fio options

The parent manifest must record:

- planned and observed file bytes: `34359738368`
- completion-based execution
- `1M`, QD4, direct=1, numjobs=1, windowsaio
- both phases `complete`
- explicit USB/file-target interpretation boundary

## 7. Post-Run Validation

```powershell
$experiment = "large_ws_seq_32g_20260724"
$writeRun = "sustained_${experiment}_seqwrite_32g_run1"
$readRun = "sustained_${experiment}_seqread_32g_run1"

Get-Item -LiteralPath "E:\validation\ssd_lab_seq_32g" |
  Select-Object FullName, Length, LastWriteTime

Get-Content -Raw ".\results\external_ssd\_experiments\$experiment\experiment_manifest.json"

foreach ($runId in @($writeRun, $readRun)) {
  $runDir = Join-Path ".\results\external_ssd" $runId
  Select-String -Path (Join-Path $runDir "*_run*.json") -Pattern '"error"|"filename"|"size"'
  python .\scripts\analysis\build_external_ssd_run_manifest.py --result-set $runId
}

python .\scripts\analysis\analyze_external_ssd_sustained.py
```

## 8. Interpretation Plan

Review write and read separately:

- transferred bytes and completion time
- average bandwidth and IOPS
- p99, p99.9, and maximum completion latency
- first/middle/last-third bandwidth
- last/first bandwidth and latency direction
- any abrupt transition or stall in 1-second logs
- observer and telemetry limitations

A stable result means the time-window evidence remains broadly consistent for this one pilot. A transition remains an externally observed large-working-set behavior. Do not label it SLC exhaustion, thermal throttling, FTL behavior, or GC without independent evidence.

One pilot is an observation. Repeat it only if the time series exposes a material behavior worth testing for reproducibility.

## 9. Failure Handling

- Existing target file: stop and inspect it; do not overwrite automatically.
- Insufficient free space or unhealthy E: volume: do not run.
- fio nonzero exit: preserve raw output and failed manifests.
- Write file length not exactly 32 GiB: classify the experiment as failed.
- Observer limitation: preserve it as `limited`; do not fabricate telemetry.
- Interrupted write: retain raw evidence and inspect the partial external file before deciding on cleanup.
- Wrong drive letter or physical port: do not classify the run as valid evidence.
