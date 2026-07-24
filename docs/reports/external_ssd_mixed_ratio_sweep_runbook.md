# External SSD Counterbalanced Mixed-Ratio Sweep Runbook

## Purpose

Test protocol: `EXT-MIXED-RATIO-SWEEP-001`

Question:

> How do read and write response metrics vary across 90:10, 70:30, and 50:50 mixes when every ratio occupies every sequence position once?

The preceding ABBA/BAAB read-tail hypothesis was `not reproduced`. This sweep
is therefore descriptive response mapping. It is not a causal test of
write-induced read-tail inflation.

## Counterbalanced Sequence

```text
10-minute confirmed disconnect
  -> same-port reconnect
  -> 5-minute initial idle
  -> cycle 1: 90:10 -> 70:30 -> 50:50
  -> 5-minute cycle idle
  -> cycle 2: 70:30 -> 50:50 -> 90:10
  -> 5-minute cycle idle
  -> cycle 3: 50:50 -> 90:10 -> 70:30
```

Use a 60-second idle between phases inside each cycle.

Every phase uses:

```text
target=E:\validation\ssd_lab_seq_32g
rw=randrw
bs=4k
iodepth=16
size=32G
runtime=180s
time_based=1
direct=1
ioengine=windowsaio
numjobs=1
randrepeat=1
overwrite=1
```

## Why This Order

Each ratio appears once in position 1, position 2, and position 3. This does
not remove session-state effects, but it prevents one ratio from always being
assigned to an early or late position.

Results must retain three dimensions:

```text
ratio x cycle x position
```

Do not summarize by ratio alone until the three position-specific observations
have been reviewed.

## Safety Boundary

- The target must already exist under `E:\validation\`.
- The target must be exactly `34359738368` bytes.
- Reconnect-start, same-port, and dedicated-write confirmations are mandatory.
- All nine phases modify only the dedicated file.
- The runner never targets a raw physical drive.
- Do not reuse an experiment label that already has output.

## Preflight

After the 10-minute disconnect and same-port reconnect:

```powershell
cd D:\ssd_lab

Get-Volume -DriveLetter E |
  Select-Object DriveLetter, FriendlyName, FileSystemType, HealthStatus, OperationalStatus, SizeRemaining, Size

Get-Item -LiteralPath "E:\validation\ssd_lab_seq_32g" |
  Select-Object FullName, Length, LastWriteTime

fio --version
```

Expected:

- E: is the intended external SSD
- volume status is `Healthy / OK`
- target length is `34359738368`
- fio is available in the current terminal

## Execution

Codex does not run fio. Execute locally:

```powershell
cd D:\ssd_lab

powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_mixed_ratio_sweep.ps1 `
  -ExperimentLabel "mixed_ratio_sweep_32g_20260724" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -ConfirmedDisconnectMinutes 10 `
  -InitialIdleMinutes 5 `
  -RuntimeSec 180 `
  -InterPhaseIdleSec 60 `
  -InterCycleIdleSec 300 `
  -ConfirmReconnectStart `
  -ConfirmSamePort `
  -ConfirmDedicatedFileWrite
```

Expected result set:

```text
results/external_ssd/sustained_mixed_ratio_sweep_32g_20260724/
```

Parent manifest:

```text
results/external_ssd/_experiments/mixed_ratio_sweep_32g_20260724/experiment_manifest.json
```

Plan for approximately 50 minutes after the runner starts, plus the confirmed
10-minute disconnect interval.

## Completion Criteria

- parent and runner manifests are `complete`
- nine fio JSON files report `error: 0`
- every phase contains nonzero read and write I/O
- observed byte mix is within one percentage point of the requested ratio
- each ratio appears once in every sequence position
- 1-second bandwidth, IOPS, and latency logs exist for every phase
- pre/post observer manifests exist
- the dedicated file remains exactly 32 GiB

## Analysis Plan

Report separately for read and write:

- bandwidth and IOPS
- p99 and p99.9 completion latency
- maximum completion latency
- first/middle/last time windows

Then compare:

- each ratio across positions 1, 2, and 3
- each position across the three cycles
- whether a monotonic ratio response is visible despite position variation
- whether maximum-latency anomalies agree with percentile behavior

Classify the result as a descriptive mapping. A monotonic trend may justify a
future independently replicated protocol; it is not by itself proof of an
internal mechanism.

## Failure Handling

- Preserve partial JSON, logs, and failed manifests.
- Stop if the target is missing, resized, or on the wrong drive.
- Stop if the external SSD is not on the confirmed physical port.
- Treat an incorrect read/write byte mix as a failed phase.
- Preserve observer limitations as `limited`.
