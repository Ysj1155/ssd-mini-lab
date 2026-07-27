# Controlled Block-Size Sweep Runbook

Status: completed on 2026-07-27. See `external_ssd_block_size_sweep_result.md`.

## 1. Purpose

This protocol closes the original controlled block-size roadmap item without
comparing unlike workloads. It maps 4K, 64K, and 1M under the same random-I/O
conditions:

- QD32
- 32 GiB existing dedicated file
- 30 seconds per phase
- `direct=1`, `windowsaio`, `numjobs=1`
- three observations per block size and workload

Random read and random write are separate reconnect-start sessions. Their
cross-workload comparison is descriptive because the sessions do not share
one guaranteed device state.

## 2. Counterbalanced Sequence

Both workload sessions use the same Latin-square order:

| Cycle | Position 1 | Position 2 | Position 3 |
|---:|---|---|---|
| 1 | 4K | 64K | 1M |
| 2 | 64K | 1M | 4K |
| 3 | 1M | 4K | 64K |

Every block size appears once in each cycle and once in each sequence
position. This prevents a fixed small-to-large order from becoming
indistinguishable from elapsed-time or phase-position effects.

The runner applies a five-minute initial idle after pre-session observation
and a uniform 60-second idle between phases.

## 3. Safety Boundary

- Target only `E:\validation\ssd_lab_seq_32g`.
- The target must already exist and be exactly 32 GiB.
- Never substitute a physical-drive path.
- The read session adds fio `--readonly`.
- The write session overwrites only the dedicated test file.
- Keep the external SSD on the same physical USB port.

## 4. Preflight

Before each independent session:

1. Safely disconnect the external SSD for at least 10 minutes.
2. Reconnect it to the same physical USB port.
3. Close applications that may access E:.
4. Verify the target and volume.

```powershell
cd D:\ssd_lab

Get-Item E:\validation\ssd_lab_seq_32g |
  Select-Object FullName, Length, LastWriteTime

Get-Volume -DriveLetter E
```

Expected file length:

```text
34359738368
```

## 5. Session 1: Random Read

After the disconnect/reconnect preflight:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_block_size_sweep.ps1 `
  -Workload randread `
  -ExperimentLabel "block_size_randread_32g_20260726" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -ConfirmedDisconnectMinutes 10 `
  -InitialIdleMinutes 5 `
  -RuntimeSec 30 `
  -InterPhaseIdleSec 60 `
  -ConfirmReconnectStart `
  -ConfirmSamePort
```

Expected duration after starting the runner is about 19 minutes.

Analyze the completed read session:

```powershell
python .\scripts\analysis\analyze_external_ssd_block_size_sweep.py `
  --experiment-label block_size_randread_32g_20260726
```

Do not start the write session until the read session has completed and the
external SSD has again been safely disconnected for at least 10 minutes.

## 6. Session 2: Random Write

After a new disconnect/reconnect preflight:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_block_size_sweep.ps1 `
  -Workload randwrite `
  -ExperimentLabel "block_size_randwrite_32g_20260726" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -ConfirmedDisconnectMinutes 10 `
  -InitialIdleMinutes 5 `
  -RuntimeSec 30 `
  -InterPhaseIdleSec 60 `
  -ConfirmReconnectStart `
  -ConfirmSamePort `
  -ConfirmDedicatedFileWrite
```

Expected duration after starting the runner is about 19 minutes. The fio
write workload totals 270 seconds across all nine phases.

Analyze the completed write session:

```powershell
python .\scripts\analysis\analyze_external_ssd_block_size_sweep.py `
  --experiment-label block_size_randwrite_32g_20260726
```

## 7. Paired Analysis and Traceability

After both session analyzers succeed:

```powershell
python .\scripts\analysis\analyze_external_ssd_block_size_sweep.py `
  --read-experiment-label block_size_randread_32g_20260726 `
  --write-experiment-label block_size_randwrite_32g_20260726

python .\scripts\analysis\build_external_ssd_run_manifest.py `
  --result-set sustained_block_size_randread_32g_20260726

python .\scripts\analysis\build_external_ssd_run_manifest.py `
  --result-set sustained_block_size_randwrite_32g_20260726
```

Per-session analysis artifacts:

- `phase_summary.csv`
- `block_size_summary.csv`
- `cycle_position_summary.csv`
- `analysis_manifest.json`

Paired artifacts are written under the write-session analysis directory:

- `cross_workload_comparison.csv`
- `verdict.csv`
- `paired_analysis_manifest.json`

## 8. Completion Checks

Each session requires:

- 9 fio JSON files with `error: 0`
- 45 one-second log files
- exactly three observations for each block size
- each block size represented once in positions 1, 2, and 3
- matching workload direction with no opposite-direction I/O
- pre/post observer manifests
- complete experiment, runner, analysis, and integrated run manifests

## 9. Interpretation Plan

Review each workload independently first:

- bandwidth and IOPS scaling from 4K to 64K to 1M
- p99 and p99.9 latency scaling
- repeat CV for each block size
- cycle and position movement relative to block-size separation
- isolated maximum-latency events

Only then compare read and write descriptively at each block size.

Do not interpret this as sequential performance: all three block sizes use
random offsets. Do not attribute a result to USB, cache, firmware, thermal
state, FTL, GC, or NAND without independent evidence.
