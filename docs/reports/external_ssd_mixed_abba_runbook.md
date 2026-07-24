# External SSD Mixed Read-QoS ABBA Runbook

## Purpose

Test protocol: `EXT-MIXED-READ-QOS-ABBA-001`

Question:

> Does adding 30% random writes inflate read p99/p99.9 under matched QD16 conditions after controlling sequence position with A-B-B-A?

Definitions:

```text
A = 100% randread
B = randrw, 70% read / 30% write
```

## Fixed Sequence

```text
same physical USB port
  -> verify existing 32 GiB target
  -> 5-minute initial idle
  -> A1: pure randread, 180s
  -> 60-second idle
  -> B1: randrw 70:30, 180s
  -> 60-second idle
  -> B2: randrw 70:30, 180s
  -> 60-second idle
  -> A2: pure randread, 180s
```

All phases use:

```text
target=E:\validation\ssd_lab_seq_32g
bs=4k
iodepth=16
size=32G
time_based=1
direct=1
ioengine=windowsaio
numjobs=1
randrepeat=1
```

A phases add `readonly`. B phases add `rwmixread=70` and `overwrite=1`.

## Safety Boundary

- The target must already exist under `E:\validation\`.
- The target must be exactly `34359738368` bytes.
- Explicit same-port and dedicated-write confirmations are required.
- A phases do not modify the target.
- B phases modify only the dedicated target file.
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
  -File .\scripts\runners\run_external_ssd_mixed_abba.ps1 `
  -ExperimentLabel "mixed_read_qos_abba_32g_20260724" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -InitialIdleMinutes 5 `
  -RuntimeSec 180 `
  -InterPhaseIdleSec 60 `
  -ConfirmSamePort `
  -ConfirmDedicatedFileWrite
```

Expected result set:

```text
sustained_mixed_read_qos_abba_32g_20260724
```

Parent manifest:

```text
results/external_ssd/_experiments/mixed_read_qos_abba_32g_20260724/experiment_manifest.json
```

Expected duration is approximately 20 minutes including idle intervals and observer collection.

## Completion Criteria

- parent and runner manifests are `complete`
- A1, B1, B2, and A2 are all `complete`
- four fio JSON files report `error: 0`
- A phases contain read I/O and zero write I/O
- B phases contain both read and write I/O near the 70:30 byte ratio
- each phase has 1-second bandwidth, IOPS, and latency logs
- pre/post observer manifests exist
- the dedicated file remains exactly 32 GiB

## Comparison Plan

Review:

- A2/A1 read bandwidth, p99, and p99.9
- B2/B1 read bandwidth, p99, and p99.9
- mean B read p99/p99.9 divided by mean A read p99/p99.9
- first/middle/last windows for all four phases
- whether B-phase read/write dips occur at the same timestamps
- whether A2 recovers after the two B phases

Do not interpret B/A bandwidth directly as a loss percentage because A and B issue different operation mixes through the same QD16 queue.

## Sweep Gate Result

The ABBA result did not satisfy the causal sweep gate because B1 and B2 did not agree. An independent reconnect-start BAAB session was therefore run. ABBA and BAAB then produced opposite B2/B1 directions, so the original read-tail hypothesis was closed as `not reproduced`.

## Prepared Ratio-Sweep Design

The planned ratios are:

```text
90:10
70:30
50:50
```

The follow-on uses three counterbalanced cycles so each ratio appears once in each sequence position:

```text
cycle 1: 90:10 -> 70:30 -> 50:50
cycle 2: 70:30 -> 50:50 -> 90:10
cycle 3: 50:50 -> 90:10 -> 70:30
```

Hold `4K`, QD16, 32 GiB, 180 seconds, direct I/O, one job, and the random sequence constant. Use 60-second phase idle and a longer fixed idle between cycles. The sweep is descriptive ratio-by-cycle-by-position mapping, not causal confirmation.
## Interpretation Boundary

ABBA reduces simple first-versus-last order bias inside one connected session. It does not create independent reconnect replicates and cannot identify USB, OS, thermal, cache, FTL, GC, or NAND root cause.

## Failure Handling

- Preserve partial JSON, logs, and failed manifests.
- Do not reuse an experiment label that already contains output.
- Stop if the target is missing or has the wrong size.
- Treat an incorrect A or B operation mix as a failed phase.
- Preserve observer limitations explicitly.
