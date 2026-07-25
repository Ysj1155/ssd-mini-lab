# External SSD Mixed-Ratio Cross-Session Result

## Status

Study: `mixed_ratio_sweep_cross_session`

Sessions:

- `mixed_ratio_sweep_32g_20260724`
- `mixed_ratio_sweep_repro2_32g_20260724`

Requirement verdict: `REQ-MIXED-RATIO-REPRO-006 = Pass`

Performance verdict:

```text
not_reproduced_across_independent_counterbalanced_sessions
```

Both independently initiated sessions completed all nine phases with matching
4K, QD16, 32 GiB, direct-I/O, runtime, idle, and evidence controls. Requirement
completion is separate from performance-direction reproduction.

## Automated Evidence

The dedicated analyzer now generates:

- `transition_summary.csv`
- `cross_session_ratio_comparison.csv`
- `cross_session_verdict.csv`

Transition time is defined as:

> The first timestamp at which total bandwidth remains at or above 80% of the
> last-third mean for five consecutive one-second samples.

This is an external time-series metric. It is not a device-state or firmware
event marker.

## Ratio Comparison

| Ratio | Session 1 total BW MiB/s | Session 2 total BW MiB/s | Change | Session 1 BW rank | Session 2 BW rank |
|---|---:|---:|---:|---:|---:|
| 90:10 | 109.215 | 194.300 | +77.9% | 2 | 1 |
| 70:30 | 129.522 | 182.035 | +40.5% | 1 | 2 |
| 50:50 | 102.474 | 167.360 | +63.3% | 3 | 3 |

Bandwidth rank changed from:

```text
Session 1: 70:30 > 90:10 > 50:50
Session 2: 90:10 > 70:30 > 50:50
```

Read-p99 rank also changed:

```text
Session 1: 70:30 > 50:50 > 90:10
Session 2: 90:10 > 70:30 > 50:50
```

Here `>` means better performance: higher bandwidth or lower latency.

## Session-Level Difference

| Metric | Session 1 | Session 2 |
|---|---:|---:|
| Mean total BW MiB/s | 113.737 | 181.231 |
| Mean read p99 ms | 2.368 | 0.635 |
| Mean read p99.9 ms | 5.071 | 1.089 |
| Cycle BW rank | 3 > 2 > 1 | 1 > 3 > 2 |
| Position BW rank | 1 > 2 > 3 | 3 > 2 > 1 |

Ratio, cycle, and position directions did not reproduce.

## Transition Comparison

| Metric | Session 1 | Session 2 |
|---|---:|---:|
| Median transition time | 1.003 s | 44.046 s |
| 30-60 s ramp phases | 0 / 9 | 8 / 9 |
| Phase 5 ratio | 50:50 | 90:10 |
| Phase 5 last/first BW | 0.524x | 1.384x |
| Phase 5 direction | Drop | Rise |

Session 1 contained one late Phase 2 rise and one persistent Phase 5 drop.
Session 2 instead showed a session-wide ramp: read and write bandwidth rose
together in nearly every phase after roughly 37-53 seconds.

Changing Phase 5 from 50:50 to 90:10 reversed its direction. The original
Phase 5 drop therefore did not follow temporal position into the independent
session and did not reproduce as a ratio-independent phase effect.

## Verdict

- Both evidence protocols passed.
- Session 1 ratio rank did not reproduce.
- Session 1 cycle and position ranks did not reproduce.
- Session 1 Phase 5 drop did not reproduce.
- Session 2's systematic 30-60 second ramp was absent from Session 1.

The strongest defensible result is session-level black-box state variation,
not a stable ratio, cycle, position, or phase-transition characteristic.

No third full ratio sweep should be added merely to search for agreement. A
future experiment should isolate pre-probe idle duration while holding one
ratio fixed and use the automated transition-time metric as its primary
response.

## Evidence

- `results/external_ssd/sustained_mixed_ratio_sweep_32g_20260724/analysis/transition_summary.csv`
- `results/external_ssd/sustained_mixed_ratio_sweep_repro2_32g_20260724/analysis/transition_summary.csv`
- `results/external_ssd/sustained_mixed_ratio_sweep_repro2_32g_20260724/analysis/cross_session_ratio_comparison.csv`
- `results/external_ssd/sustained_mixed_ratio_sweep_repro2_32g_20260724/analysis/cross_session_verdict.csv`
- `results/external_ssd/sustained_mixed_ratio_sweep_repro2_32g_20260724/analysis/analysis_manifest.json`

Observer limitations remain unchanged: SMART and storage reliability evidence
were unavailable through the current Windows access path. The results cannot
identify USB, host power state, OS, filesystem, thermal, cache, firmware, FTL,
GC, or NAND root cause.
