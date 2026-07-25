# External SSD Counterbalanced Mixed-Ratio Sweep Result

## Status

Protocol: `EXT-MIXED-RATIO-SWEEP-001`

Execution status: `complete`

Requirement verdict: `REQ-MIXED-RATIO-005 = Pass`

Classification: `descriptive_ratio_by_cycle_by_position_mapping`

The sweep completed all nine planned phases with exact counterbalancing. It
does not reopen the ABBA/BAAB causal hypothesis, which remains `not reproduced`.

## Conditions

```text
target: E:\validation\ssd_lab_seq_32g
target size: 32 GiB
bs: 4K
iodepth: 16
runtime: 180 seconds per phase
direct: 1
ioengine: windowsaio
initial idle: 300 seconds
inter-phase idle: 60 seconds
inter-cycle idle: 300 seconds
```

The session began after a user-confirmed 600-second disconnect and same-port
reconnect. All phases wrote only to the dedicated file target.

## Sequence

```text
cycle 1: 90:10 -> 70:30 -> 50:50
cycle 2: 70:30 -> 50:50 -> 90:10
cycle 3: 50:50 -> 90:10 -> 70:30
```

The observed read shares remained within 0.04 percentage points of the
requested ratios.

## Phase Results

| Phase | Cycle | Position | Ratio | Total BW MiB/s | Read p99 ms | Read p99.9 ms |
|---:|---:|---:|---|---:|---:|---:|
| 1 | 1 | 1 | 90:10 | 93.829 | 3.097 | 6.324 |
| 2 | 1 | 2 | 70:30 | 70.261 | 4.145 | 8.454 |
| 3 | 1 | 3 | 50:50 | 61.282 | 4.555 | 9.372 |
| 4 | 2 | 1 | 70:30 | 156.208 | 0.643 | 1.057 |
| 5 | 2 | 2 | 50:50 | 118.377 | 1.352 | 5.931 |
| 6 | 2 | 3 | 90:10 | 54.649 | 5.341 | 9.634 |
| 7 | 3 | 1 | 50:50 | 127.764 | 0.905 | 2.343 |
| 8 | 3 | 2 | 90:10 | 179.167 | 0.602 | 1.106 |
| 9 | 3 | 3 | 70:30 | 162.097 | 0.676 | 1.417 |

## Ratio Summary

| Ratio | Mean total BW MiB/s | Range | BW CV | Mean read p99 ms | Mean read p99.9 ms |
|---|---:|---:|---:|---:|---:|
| 90:10 | 109.215 | 54.649-179.167 | 0.583 | 3.013 | 5.688 |
| 70:30 | 129.522 | 70.261-162.097 | 0.397 | 1.821 | 3.643 |
| 50:50 | 102.474 | 61.282-127.764 | 0.351 | 2.271 | 5.882 |

The balanced session mean was highest for 70:30, but the within-ratio ranges
were large. There was no monotonic total-throughput or read-tail penalty as
write share increased. The observed rank is a session-level description, not
an established product characteristic.

## Cycle and Position Effects

| Cycle | Mean total BW MiB/s | Mean read p99 ms | Mean read p99.9 ms |
|---:|---:|---:|---:|
| 1 | 75.124 | 3.932 | 8.050 |
| 2 | 109.744 | 2.445 | 5.541 |
| 3 | 156.343 | 0.728 | 1.622 |

Cycle movement was larger than the ratio means. Position 3 also had the lowest
mean total bandwidth and highest mean read tail, but three samples are not
enough to separate a stable position effect from phase-specific state changes.

## Automatically Flagged Anomalies

The analyzer used predeclared generic thresholds:

- last/first total-bandwidth ratio at or below 0.70 or at or above 1.30
- maximum completion latency at or above 100 ms

It flagged:

| Phase | Ratio | Finding |
|---:|---|---|
| 2 | 70:30 | Last/first total BW 1.553x |
| 2 | 70:30 | Maximum completion latency 124.554 ms |
| 5 | 50:50 | Last/first total BW 0.524x |

Phase 5 remained near 132-148 MiB/s through most of the first 130 seconds,
then fell to roughly 44-53 MiB/s near the end. Phase 6 remained near 55 MiB/s
after a 60-second idle. Phase 7 returned above 123 MiB/s after the 300-second
cycle boundary.

This is an externally observed state sequence. It does not prove that the
longer idle caused recovery and does not identify USB, OS, filesystem, cache,
FTL, GC, NAND, firmware, or thermal root cause.

## Verdict

- The execution and evidence requirement passed.
- Requested read/write mixes were reproduced accurately.
- A monotonic write-share penalty was not observed.
- Ratio averages were smaller than the cross-cycle and within-ratio variation.
- One independent session is insufficient to establish the ratio ranking or
  the Phase 5 transition as repeatable.

The independent `EXT-MIXED-RATIO-SWEEP-REPRO-002` follow-on completed with
Phase 5 changed from 50:50 to 90:10. It did not reproduce the ratio, cycle,
position, or Phase 5 directions. See
`docs/reports/external_ssd_mixed_ratio_cross_session_result.md`.

## Evidence Chain

- `results/external_ssd/_experiments/mixed_ratio_sweep_32g_20260724/experiment_manifest.json`
- `results/external_ssd/sustained_mixed_ratio_sweep_32g_20260724/runner_manifest.json`
- `results/external_ssd/sustained_mixed_ratio_sweep_32g_20260724/observer_manifest_pre.json`
- `results/external_ssd/sustained_mixed_ratio_sweep_32g_20260724/observer_manifest_post.json`
- `results/external_ssd/sustained_mixed_ratio_sweep_32g_20260724/analysis/analysis_manifest.json`
- `results/external_ssd/sustained_mixed_ratio_sweep_32g_20260724/analysis/*.csv`

Observer status remains Limited because SMART and storage reliability evidence
was unavailable through the current Windows access path.
