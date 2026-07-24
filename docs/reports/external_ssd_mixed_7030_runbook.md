# External SSD Mixed 70:30 Runbook

## Purpose

Test protocol: `EXT-MIXED-RW-7030-001`

Question:

> How do read and write throughput and tail latency behave when 4K random reads and writes are issued concurrently at a synthetic 70:30 ratio?

This is a controlled synthetic interference workload. It is not a customer trace or an enterprise workload model.

## Fixed Conditions

```text
target file: E:\validation\ssd_lab_seq_32g (existing exact 32 GiB file)
rw=randrw
rwmixread=70
rwmixwrite=30
bs=4k
iodepth=16
size=32G
runtime=180s
time_based=1
direct=1
ioengine=windowsaio
numjobs=1
randrepeat=1
repeat=3
initial idle=5m
inter-run idle=60s
```

The fixed random sequence improves run-to-run comparability. The three repeats are process repeats inside one connected session, not independent reconnect sessions.

## Safety Boundary

The workload modifies this dedicated file:

```text
E:\validation\ssd_lab_seq_32g
```

The runner:

- refuses paths outside `E:\validation\`
- requires the target to exist and be exactly `34359738368` bytes
- requires explicit same-port and dedicated-write confirmations
- uses `overwrite=1`
- never targets a raw physical drive
- writes no other external-SSD file

## Preflight

Use the same physical USB port as the completed 32 GiB sequential pilot.

```powershell
cd D:\ssd_lab

Get-Volume -DriveLetter E |
  Select-Object DriveLetter, FriendlyName, FileSystemType, HealthStatus, OperationalStatus, SizeRemaining, Size

Get-Item -LiteralPath "E:\validation\ssd_lab_seq_32g" |
  Select-Object FullName, Length, LastWriteTime
```

Expected:

- E: is the intended external SSD
- `HealthStatus` is `Healthy`
- `OperationalStatus` contains `OK`
- target length is exactly `34359738368`

Stop if any condition differs.

## Execution

Codex does not run fio. Execute locally:

```powershell
cd D:\ssd_lab

powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_mixed_7030.ps1 `
  -ExperimentLabel "mixed_7030_32g_20260724" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -InitialIdleMinutes 5 `
  -RuntimeSec 180 `
  -Runs 3 `
  -InterRunIdleSec 60 `
  -ConfirmSamePort `
  -ConfirmDedicatedFileWrite
```

Expected result set:

```text
sustained_mixed_7030_32g_20260724_randrw_7030_4k_qd16_repeat3
```

Parent manifest:

```text
results/external_ssd/_experiments/mixed_7030_32g_20260724/experiment_manifest.json
```

## Completion Criteria

The result is structurally complete when:

- three fio JSON files report `error: 0`
- every JSON contains nonzero read and write `io_bytes`
- per-run bandwidth, IOPS, and latency logs exist
- `runner_manifest.json` is `complete`
- pre/post observer manifests exist
- all three parent-manifest phases are `complete`
- the dedicated file still exists at exactly 32 GiB

## Interpretation

Review read and write separately:

- bandwidth and IOPS
- p99 and p99.9 completion latency
- run-to-run CV
- first/middle/last time windows
- rare maximum latency versus sustained interval behavior
- observer and telemetry limitations

Do not combine read and write latency into one QoS number. Do not claim that the 70:30 ratio represents a real customer workload without an external requirement or trace. Do not infer cache, FTL, GC, NAND, or thermal root cause from this workload alone.

## Failure Handling

- Preserve partial JSON, logs, and failed manifests.
- Do not reuse an experiment label that already has raw output.
- If the target is missing or has the wrong size, stop and inspect it.
- If either read or write `io_bytes` is zero, classify the run as failed.
- Keep observer limitations explicit instead of fabricating unavailable telemetry.
