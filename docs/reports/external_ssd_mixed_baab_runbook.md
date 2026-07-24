# External SSD Independent BAAB Runbook

## Purpose

Test protocol: `EXT-MIXED-READ-QOS-BAAB-002`

Question:

> Does an independent reconnect-start B-A-A-B session reproduce mixed read-QoS behavior after reversing the workload order?

Definitions:

```text
A = 100% randread
B = randrw, 70% read / 30% write
```

## Independent-Session Start

Before running:

1. Safely eject the external SSD.
2. Disconnect it for at least 10 minutes.
3. Reconnect it to the same physical USB port.
4. Confirm that it is mounted as E: and the target is present.
5. Start the runner, which applies another 5-minute idle before B1.

Reconnect-start is an externally controlled condition. It does not prove that the SSD reached an internally reset or cold state.

## Fixed Sequence

```text
10-minute confirmed disconnect
  -> same-port reconnect
  -> 5-minute initial idle
  -> B1: randrw 70:30, 180s
  -> 60-second idle
  -> A1: pure randread, 180s
  -> 60-second idle
  -> A2: pure randread, 180s
  -> 60-second idle
  -> B2: randrw 70:30, 180s
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
- Reconnect-start, same-port, and dedicated-write confirmations are mandatory.
- A phases do not modify the target.
- B phases modify only the dedicated target file.
- The runner never targets a raw physical drive.

## Preflight

Run after reconnecting:

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
  -File .\scripts\runners\run_external_ssd_mixed_baab.ps1 `
  -ExperimentLabel "mixed_read_qos_baab_32g_20260724" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -ConfirmedDisconnectMinutes 10 `
  -InitialIdleMinutes 5 `
  -RuntimeSec 180 `
  -InterPhaseIdleSec 60 `
  -ConfirmReconnectStart `
  -ConfirmSamePort `
  -ConfirmDedicatedFileWrite
```

Expected result set:

```text
sustained_mixed_read_qos_baab_32g_20260724
```

Parent manifest:

```text
results/external_ssd/_experiments/mixed_read_qos_baab_32g_20260724/experiment_manifest.json
```

The runner takes approximately 20 minutes after it starts. Including the confirmed disconnect interval, plan for about 30 minutes.

## Completion Criteria

- parent and runner manifests are `complete`
- B1, A1, A2, and B2 are all `complete`
- four fio JSON files report `error: 0`
- A phases contain read I/O and zero write I/O
- B phases contain both read and write I/O near the 70:30 byte ratio
- each phase has 1-second bandwidth, IOPS, and latency logs
- pre/post observer manifests exist
- the dedicated file remains exactly 32 GiB

## Joint ABBA/BAAB Comparison

Compare:

- BAAB B2/B1 read bandwidth, p99, and p99.9
- BAAB A2/A1 read bandwidth, p99, and p99.9
- ABBA and BAAB B-position results
- whether the second B is consistently slower regardless of position
- whether consecutive equal phases behave differently from separated phases
- whether A remains recoverable after B
- first/middle/last time windows for all phases

Interpretation:

- Similar BAAB B1/B2 with dissimilar ABBA B1/B2 suggests adjacency or transient state in ABBA.
- BAAB B2 degradation again suggests elapsed-time or cumulative-workload influence.
- Irregular B direction across both sessions means ratio sweep remains premature.
- Stable A and consistently worse B tail across both sequences supports mixed read-QoS interference.

## Sweep Gate Result

BAAB reversed the ABBA B2/B1 direction. The repeatable mixed read-tail inflation hypothesis is therefore `not reproduced`, while the ABBA and BAAB evidence requirements pass.

The follow-on `90:10 / 70:30 / 50:50` sweep is allowed only as descriptive response mapping. It retains cycle and position explicitly and cannot be used as causal confirmation of the closed hypothesis.
## Interpretation Boundary

ABBA and BAAB reduce simple order bias but do not identify USB, OS, thermal, cache, FTL, GC, NAND, or firmware root cause. Observer limitations must remain visible.

## Failure Handling

- Preserve partial JSON, logs, and failed manifests.
- Do not reuse an experiment label that already contains output.
- Stop if reconnect uses a different port or drive letter.
- Stop if the target is missing or has the wrong size.
- Treat an incorrect A or B operation mix as a failed phase.
- Preserve observer limitations explicitly.
