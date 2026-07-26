# External SSD Execution Runbook

Codex prepares and reviews external SSD workflows but does not run fio unless explicitly asked. The user confirms the target and executes the prepared PowerShell runner locally.

## 1. Completed Checkpoint

`EXT-STATE-REPRO-002` completed three separately initiated paired sessions. Its bandwidth deltas were -6.37%, -7.59%, and +23.33%, so the conditioning-uplift direction was not reproduced.

The state study is closed. Do not add sessions merely to search for a preferred direction.

## 2. Completed Large-Working-Set Experiment

Test protocol: `EXT-LARGE-WS-SEQ-001`

Question:

> Does sequential throughput remain stable while completing one 32 GiB write and one 32 GiB read?

Fixed sequence:

```text
same physical USB port
  -> verify E: health and at least 40 GiB free
  -> confirm dedicated target does not exist
  -> create and verify the dedicated 32 GiB target
  -> 5-minute idle
  -> overwrite 32 GiB sequentially, bs=1M, QD4, direct=1, run=1
  -> verify exact 32 GiB file length
  -> 60-second idle
  -> 32 GiB sequential readonly read, bs=1M, QD4, direct=1, run=1
```

Both fio phases are completion-based. They do not use `time_based` or repeatedly wrap a small file. The runner creates the exact-size target before the initial idle and passes `overwrite=1` to fio, so Windows fio operates on an existing dedicated file that remains available for the read phase.

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
- creates and verifies the exact 32 GiB file before the initial idle
- uses fio `overwrite=1` for both measured phases
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
- Interrupted setup or write: retain raw evidence and inspect the external file before deciding on cleanup.
- Wrong drive letter or physical port: do not classify the run as valid evidence.

## 10. Completed Mixed Read-QoS Decision

The A-B-B-A and independent reconnect-start B-A-A-B sessions completed with matching 4K, QD16, 32 GiB, and 180-second controls. Their second mixed phases moved in opposite directions:

- ABBA B2/B1: read bandwidth 0.712x, p99 1.345x, p99.9 3.925x
- BAAB B2/B1: read bandwidth 1.224x, p99 0.910x, p99.9 0.724x

The repeatable mixed read-tail inflation hypothesis is `not_reproduced_under_controlled_abba_baab_sequences`. Both evidence requirements pass because the planned sessions and comparisons exist.

See [external_ssd_mixed_abba_baab_result.md](external_ssd_mixed_abba_baab_result.md).

## 11. Completed Counterbalanced Ratio Mapping

`EXT-MIXED-RATIO-SWEEP-001` completed all nine phases with accurate 90:10, 70:30, and 50:50 byte mixes. The generated analysis preserves phase, ratio, cycle, position, first/middle/last windows, and anomaly flags.

Observed Session 1 findings:

- no monotonic total-throughput or read-tail penalty as write share increased
- ratio mean total BW: 90:10 = 109.215, 70:30 = 129.522, 50:50 = 102.474 MiB/s
- cycle mean total BW: 75.124, 109.744, and 156.343 MiB/s
- Phase 5 last/first total BW = 0.524x
- Phase 2 last/first total BW = 1.553x with a 124.554 ms maximum latency

At the Session 1 checkpoint, the requirement passed while ratio ranking and phase-transition behavior remained single-session observations.

See [external_ssd_mixed_ratio_sweep_result.md](external_ssd_mixed_ratio_sweep_result.md).

## 12. Completed Independent Ratio Reproduction

`EXT-MIXED-RATIO-SWEEP-REPRO-002` completed all nine Session 2 phases and the dedicated analyzer generated transition and cross-session evidence.

Automated verdict:

```text
requirement_verdict: Pass
performance_verdict: not_reproduced_across_independent_counterbalanced_sessions
```

Key disagreements:

- ratio BW rank: `70:30 > 90:10 > 50:50` vs `90:10 > 70:30 > 50:50`
- cycle rank: `3 > 2 > 1` vs `1 > 3 > 2`
- position rank: `1 > 2 > 3` vs `3 > 2 > 1`
- Phase 5: 0.524x drop vs 1.384x rise
- 30-60 second ramp: 0/9 vs 8/9 phases

See [external_ssd_mixed_ratio_cross_session_result.md](external_ssd_mixed_ratio_cross_session_result.md).

## 13. Completed Idle-Ramp Decision

A third full ratio sweep was not added merely to search for agreement.
`EXT-IDLE-RAMP-001` tested whether the Session 2 phase-start ramp depended on
pre-probe idle duration while ratio, QD, runtime, target, random sequence, and
physical port remained fixed.

```text
fixed workload: 70:30, 4K, QD16, 32 GiB, 120s
pre-probe idle sequence: 300s -> 60s -> 0s -> 0s -> 60s -> 300s
primary metric: automated transition_sec
```

The mirrored `A-B-C-C-B-A` sequence placed each idle condition in both an
early and a late phase. All six phases completed, but none reproduced the
prior 37-53 second ramp. The automated verdict is
`no_clear_idle_duration_association`.

See [external_ssd_idle_ramp_result.md](external_ssd_idle_ramp_result.md).