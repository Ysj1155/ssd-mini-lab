# External SSD Matched Mixed Controls Runbook

## Purpose

Test protocol: `EXT-MIXED-CONTROL-001`

Question:

> How do the 70:30 mixed results compare with matched 100% random-read and 100% random-write controls?

These controls preserve the mixed experiment's `4K`, QD16, 32 GiB, 180-second, direct-I/O conditions. They provide comparison baselines; they are not additional mixed ratios.

## Sequence

```text
same physical USB port
  -> verify existing 32 GiB target
  -> 5-minute initial idle
  -> 100% randread, 180s, repeat=3, 60s inter-run idle
  -> 5-minute transition idle
  -> 100% randwrite, 180s, repeat=3, 60s inter-run idle
```

Read runs first so the pure-read control is not immediately preceded by the write-control workload. The sequence order is fixed and must remain visible in the interpretation.

## Fixed Conditions

```text
target=E:\validation\ssd_lab_seq_32g
bs=4k
iodepth=16
size=32G
runtime=180s
time_based=1
direct=1
ioengine=windowsaio
numjobs=1
randrepeat=1
repeat=3 per control
inter-run idle=60s
```

The read control adds `readonly`. The write control adds `overwrite=1`.

## Safety Boundary

- The target must already exist under `E:\validation\`.
- The target must be exactly `34359738368` bytes.
- Explicit same-port and dedicated-write confirmations are required.
- The read set does not modify the target.
- The write set modifies only the dedicated target file.
- The runner never targets a raw physical drive.

## Preflight

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
- target length is `34359738368`

## Execution

Codex does not run fio. Execute locally:

```powershell
cd D:\ssd_lab

powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_mixed_controls.ps1 `
  -ExperimentLabel "mixed_control_32g_20260724" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -InitialIdleMinutes 5 `
  -TransitionIdleMinutes 5 `
  -RuntimeSec 180 `
  -Runs 3 `
  -InterRunIdleSec 60 `
  -ConfirmSamePort `
  -ConfirmDedicatedFileWrite
```

Expected result sets:

```text
sustained_mixed_control_32g_20260724_randread_4k_qd16_repeat3
sustained_mixed_control_32g_20260724_randwrite_4k_qd16_repeat3
```

Parent manifest:

```text
results/external_ssd/_experiments/mixed_control_32g_20260724/experiment_manifest.json
```

Expected duration is approximately 34 minutes including fixed idle intervals and observer collection.

## Completion Criteria

- parent manifest is `complete`
- read and write phases are both `complete`
- each result set contains three fio JSON files with `error: 0`
- the expected operation has nonzero `io_bytes` in every run
- 1-second bandwidth, IOPS, and latency logs exist for every run
- each result set has `runner_manifest.json`
- each result set has pre/post observer manifests
- the dedicated file remains exactly 32 GiB

## Comparison Plan

Compare the controls with `mixed_7030_32g_20260724`:

- mixed read bandwidth versus pure-read bandwidth
- mixed write bandwidth versus pure-write bandwidth
- per-direction p99 and p99.9 inflation
- run-to-run CV
- first/middle/last time-window direction
- whether the low-throughput run pattern appears in pure controls
- whether read and write interval changes still move together

Do not normalize mixed bandwidth merely by dividing the pure baseline by the requested ratio. The shared QD16 queue, operation mix, host path, and device scheduling make that assumption invalid.

## Interpretation Boundary

The two control sets execute sequentially in one connected session and are not independent reconnect replicates. Any difference may include session order or external state. Do not infer cache, FTL, GC, NAND, USB, OS, or thermal root cause without independent evidence.

## Failure Handling

- Preserve partial JSON, logs, and failed manifests.
- Do not reuse an experiment label that already contains raw output.
- Stop if the target is missing or has the wrong size.
- Treat missing read/write evidence or fio nonzero exit as a failed control.
- Preserve observer limitations explicitly.
