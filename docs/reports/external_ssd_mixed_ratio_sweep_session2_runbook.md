# External SSD Independent Mixed-Ratio Sweep Session 2 Runbook

## Purpose

Protocol: `EXT-MIXED-RATIO-SWEEP-REPRO-002`

Question:

> Does an independent counterbalanced session reproduce the ratio response and phase-transition pattern observed in Session 1?

This is a black-box reproducibility session. It does not test or claim an
internal SSD root cause.

## Independent Start

1. Safely eject the external SSD.
2. Disconnect it for at least 10 minutes.
3. Reconnect it to the same physical USB port.
4. Confirm E: and the dedicated 32 GiB target.
5. Start the runner, which applies another 5-minute idle.

Reconnect-start is an external condition, not proof of an internally reset
device state.

## Session 2 Sequence

```text
cycle 1: 50:50 -> 70:30 -> 90:10
cycle 2: 70:30 -> 90:10 -> 50:50
cycle 3: 90:10 -> 50:50 -> 70:30
```

Each ratio again appears once in every cycle and sequence position. Unlike
Session 1, Phase 5 is 90:10 rather than 50:50.

Fixed conditions:

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
phase idle=60s
cycle idle=300s
```

## Safety Boundary

- The target must already exist under `E:\validation\`.
- The target must be exactly `34359738368` bytes.
- Reconnect-start, same-port, and dedicated-write confirmations are mandatory.
- All writes remain inside the dedicated file target.
- The runner never targets a raw physical drive.
- Use a new experiment label.

## Preflight

Run after the disconnect and same-port reconnect:

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
  -SequenceVariant session2 `
  -ExperimentLabel "mixed_ratio_sweep_repro2_32g_20260724" `
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
results/external_ssd/sustained_mixed_ratio_sweep_repro2_32g_20260724/
```

Parent manifest:

```text
results/external_ssd/_experiments/mixed_ratio_sweep_repro2_32g_20260724/experiment_manifest.json
```

Plan for approximately 50 minutes after runner start, plus the confirmed
10-minute disconnect.

## Completion Criteria

- parent and runner manifests are `complete`
- protocol ID is `EXT-MIXED-RATIO-SWEEP-REPRO-002`
- `sequence_variant` is `session2`
- all nine fio JSON files report `error: 0`
- every phase contains the requested read/write byte mix
- each ratio occupies every cycle and position once
- all 45 one-second log files exist
- pre/post observer manifests exist
- the dedicated target remains exactly 32 GiB

After completion:

```powershell
python .\scripts\analysis\analyze_external_ssd_mixed_ratio_sweep.py `
  --experiment-label mixed_ratio_sweep_repro2_32g_20260724
```

## Predeclared Comparison

Compare Session 2 against Session 1:

- ratio mean and range for total BW, read p99, and read p99.9
- cycle and position means
- anomaly count and phase location
- whether the Session 1 70:30 mean advantage repeats
- whether Phase 5 drops despite changing from 50:50 to 90:10
- whether low performance persists across a 60-second boundary
- whether a 300-second cycle boundary is followed by higher performance

Classify a direction as reproduced only when both independent sessions agree.
Do not infer a device-internal cause from timing or idle association alone.

## Completed Result

Session 2 completed on 2026-07-24. The analyzer generated:

- `transition_summary.csv`
- `cross_session_ratio_comparison.csv`
- `cross_session_verdict.csv`

The evidence requirement passed, while ratio, cycle, position, Phase 5, and 30-60 second ramp directions did not reproduce across sessions.

See [external_ssd_mixed_ratio_cross_session_result.md](external_ssd_mixed_ratio_cross_session_result.md).
## Failure Handling

- Preserve partial JSON, logs, and failed manifests.
- Stop if the target is missing, resized, or on the wrong drive.
- Stop if the external SSD is not on the confirmed physical port.
- Treat an incorrect read/write byte mix as a failed phase.
- Preserve observer limitations as `limited`.
