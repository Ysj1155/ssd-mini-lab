# External SSD Product Validation Report

Status: QD sweep, sustained QD16/QD32 studies, state-reproducibility sessions, a 32 GiB sequential pilot, controlled mixed-workload sequences, idle-ramp challenge, and counterbalanced block-size mapping completed. Evidence requirements and performance-hypothesis verdicts are tracked separately.

## 1. Scope

This report treats the external SSD as a black-box DUT and evaluates observable product behavior through fio file-target testing.

It covers controlled conditions, repeated execution, p99/p99.9 latency, sustained time-window behavior, cross-session repeatability, evidence traceability, and interpretation limits. It does not inspect or prove internal FTL/GC behavior.

Related evidence:

- `docs/reports/external_ssd_dut_profile.md`
- `docs/reports/external_ssd_requirement_matrix.md`
- `docs/reports/external_ssd_execution_runbook.md`
- `docs/reports/external_ssd_mixed_abba_baab_result.md`
- `docs/reports/external_ssd_idle_ramp_result.md`
- `docs/reports/external_ssd_block_size_sweep_result.md`
- `docs/reports/external_ssd_project_roadmap.md`
- `configs/external_ssd_validation_matrix.yaml`
- `configs/external_ssd_dut_identity.json`
- `results/external_ssd/`
- `results/external_ssd_sustained_*.csv`
- `results/external_ssd_state_repro_pairs.csv`
- `results/external_ssd_state_repro_study_summary.csv`

## 2. DUT and Environment

| Field | Value |
|---|---|
| DUT label | `external_ssd_dut_01` |
| Vendor / model | SanDisk Extreme SSD |
| Connection | External SSD over USB path |
| File system | exFAT |
| Test target | `E:\validation\ssd_lab_fio_testfile` |
| Runner preflight | Canonical path containment plus enrolled volume/disk fingerprint |
| fio version | `fio-3.42` |
| QD32 evidence-complete run | `sustained_rand_write_300s_qd32_trace_repeat3_20260721` |
| QD16 evidence-complete run | `sustained_rand_write_120s_qd16_trace_repeat3_20260722` |

The QD32 evidence-complete run predates target-aware telemetry and therefore retains a Limited device-telemetry interpretation. The QD16 evidence-complete run used the corrected collector: pre/post evidence identifies `E:\validation\ssd_lab_fio_testfile`, E: volume, and `SanDisk Extreme SSD` over USB. SMART, reliability counters, and fsutil remained Limited and are explicitly recorded.

## 3. Execution Coverage

| Test case | Condition | Repeats | Status |
|---|---|---:|---|
| `EXT-QD-SMOKE` | 4K randread/randwrite, QD 1/4/16/32, 30s | 1 | Complete |
| `EXT-PERF-RR-QD-SWEEP` | 4K randread, QD 1/4/16/32, 30s | 3 | Complete |
| `EXT-PERF-RW-QD-SWEEP` | 4K randwrite, QD 1/4/16/32, 30s | 3 | Complete |
| `EXT-SUST-WRITE-120S` | 4K randwrite, QD16, 120s | 3 + 3 + 3 | Three sessions complete; latest execution trace complete |
| `EXT-SUST-READ-120S` | 4K randread, QD16, 120s | 3 | Complete |
| `EXT-SUST-READ-QD32-120S` | 4K randread, QD32, 120s | 3 | Complete |
| `EXT-SUST-WRITE-QD32-120S` | 4K randwrite, QD32, 120s | 3 | Complete |
| `EXT-SUST-WRITE-QD32-300S` | 4K randwrite, QD32, 300s | 3 + 3 | Two sessions complete; latest execution trace complete |
| `EXT-STATE-WRITE-RECOVERY-001` | QD16 probe x3, QD32 condition x1, QD16 probe x3 | 1 sequence | Complete; initial uplift was unstable within the session |
| `EXT-STATE-REPRO-002` | Reconnect-start QD16 baseline x1, QD32 condition x1, QD16 post x1 | 3 sessions | Complete; paired direction not reproduced |
| `EXT-LARGE-WS-SEQ-001` | 32 GiB sequential write/read, 1M QD4 | 1 sequence | Complete |
| `EXT-MIXED-READ-QOS-ABBA-001` | Pure read vs 70:30 mixed, 4K QD16, A-B-B-A | 4 phases | Complete |
| `EXT-MIXED-READ-QOS-BAAB-002` | Reconnect-start 70:30 vs pure read, B-A-A-B | 4 phases | Complete; read-tail hypothesis not reproduced |
| `EXT-MIXED-RATIO-SWEEP-001` | Counterbalanced 90:10 / 70:30 / 50:50, 4K QD16 | 9 phases | Complete; descriptive mapping |
| `EXT-IDLE-RAMP-001` | Fixed 70:30, 4K QD16; mirrored 300/60/0/0/60/300-second pre-probe idle | 6 phases | Complete; no clear idle-duration association |
| `EXT-BS-RANDREAD-001` | 4K/64K/1M random read, QD32, Latin-square positions | 9 phases | Complete |
| `EXT-BS-RANDWRITE-002` | 4K/64K/1M random write, QD32, Latin-square positions | 9 phases | Complete; 64K observed throughput knee |

The sustained analyzer retains 40 earlier fio JSON jobs. The dedicated mixed-ratio analyzer covers two nine-phase sessions and generates phase, ratio, cycle/position, window, transition, anomaly, cross-session comparison, and verdict CSVs with linked analysis manifests.

## 4. QD Sweep Observation

The repeat=3 QD sweep produced 24 JSON files against `E:\validation\ssd_lab_fio_testfile`.

| Workload | QD | Avg BW MiB/s | IOPS CV | Avg p99 us | p99 CV | Avg p99.9 us | p99.9 CV |
|---|---:|---:|---:|---:|---:|---:|---:|
| rand_read | 1 | 15.46 | 0.016 | 350.21 | 0.031 | 547.50 | 0.023 |
| rand_read | 4 | 64.00 | 0.004 | 389.80 | 0.006 | 531.80 | 0.022 |
| rand_read | 16 | 197.00 | 0.006 | 703.15 | 0.007 | 976.21 | 0.005 |
| rand_read | 32 | 257.65 | 0.002 | 1,144.15 | 0.008 | 1,591.98 | 0.006 |
| rand_write | 1 | 62.71 | 0.008 | 92.33 | 0.034 | 142.34 | 0.025 |
| rand_write | 4 | 187.98 | 0.052 | 129.02 | 0.187 | 242.35 | 0.166 |
| rand_write | 16 | 192.23 | 0.014 | 398.00 | 0.016 | 583.00 | 0.032 |
| rand_write | 32 | 193.01 | 0.021 | 1,067.69 | 0.431 | 1,600.17 | 0.456 |

Random read scaled with QD and remained repeatable. Random write throughput saturated around QD16, while QD32 added no meaningful average throughput and showed the weakest short-run tail-latency repeatability. QD32 random write was therefore selected as the sustained QoS stress condition.

## 5. Sustained Result Summary

| Result set | Avg BW MiB/s | BW CV | Avg IOPS | Avg p99 us | Avg p99.9 us | Last/first IOPS | Last/first avg clat |
|---|---:|---:|---:|---:|---:|---:|---:|
| randread 120s QD16 | 170.19 | 0.058 | 43,570 | 749.57 | 1,798.14 | 1.038 | 1.003 |
| randread 120s QD32 | 235.12 | 0.078 | 60,192 | 1,095.00 | 1,591.98 | 0.979 | 1.026 |
| randwrite 120s QD16, original | 162.96 | 0.044 | 41,717 | 516.10 | 735.91 | 1.059 | 0.950 |
| randwrite 120s QD16, 2026-07-21 | 125.13 | 0.032 | 32,034 | 950.27 | 4,560.21 | 1.162 | 0.869 |
| randwrite 120s QD16, traced 2026-07-22 | 127.19 | 0.017 | 32,561 | 667.65 | 1,313.45 | 1.078 | 0.899 |
| randwrite 120s QD32 | 141.73 | 0.051 | 36,283 | 1,226.07 | 2,124.46 | 0.974 | 1.016 |
| randwrite 300s QD32, original | 138.74 | 0.065 | 35,517 | 1,329.83 | 3,249.49 | 0.910 | 1.116 |
| randwrite 300s QD32, traced | 147.90 | 0.010 | 37,862 | 1,015.81 | 1,717.59 | 1.014 | 0.759 |

### QD16 120s Cross-Session Comparison

| Metric | Original | 2026-07-21 | Traced 2026-07-22 |
|---|---:|---:|---:|
| Avg BW MiB/s | 162.96 | 125.13 | 127.19 |
| Avg IOPS | 41,717 | 32,034 | 32,561 |
| Avg p99 us | 516.10 | 950.27 | 667.65 |
| Avg p99.9 us | 735.91 | 4,560.21 | 1,313.45 |
| BW CV | 0.044 | 0.032 | 0.017 |
| Last/first IOPS | 1.059 | 1.162 | 1.078 |

The traced session reproduced the lower QD16 throughput level: average bandwidth remained about 22% below the original session and within 1.6% of the 2026-07-21 session. The lower-throughput state is therefore no longer a one-session observation.

Tail latency did not move as one fixed package with throughput. The traced session's p99.9 was higher than the original session but 71% lower than the 2026-07-21 session. Within-session repeatability was strong, with BW CV 1.7%, p99 CV 1.2%, and p99.9 CV 7.1%.

The traced session also showed no late-run degradation. Last-third IOPS averaged 1.078x the first third, while last-third average completion latency was 0.899x the first third. The defensible conclusion is that QD16 has entered a reproducible lower-throughput regime across two sessions, while severe tail-latency inflation remains intermittent and is not determined by throughput level alone.

## 6. QD32 300s Cross-Session Comparison

| Metric | Original session | Traced session | Change |
|---|---:|---:|---:|
| Avg BW MiB/s | 138.74 | 147.90 | +6.6% |
| Avg IOPS | 35,517 | 37,862 | +6.6% |
| Avg p99 us | 1,329.83 | 1,015.81 | -23.6% |
| Avg p99.9 us | 3,249.49 | 1,717.59 | -47.1% |
| BW CV | 0.065 | 0.010 | Better within-session repeatability |
| Last/first IOPS | 0.910 | 1.014 | Late-run decline not reproduced |

The traced session did not reproduce the original session's late-run throughput decline. Average throughput and p99/p99.9 were also better. The defensible conclusion is therefore cross-session variability, not deterministic degradation caused by 300 seconds at QD32.

The traced session did expose rare maximum-latency outliers:

| Run | Max completion latency |
|---:|---:|
| 1 | 0.531 s |
| 2 | 6.069 s |
| 3 | 5.713 s |

These stalls are too rare to dominate p99.9 but are operationally important. They remain black-box anomalies. The available evidence does not isolate USB transport, Windows scheduling, filesystem behavior, background activity, or SSD internal state as the cause.

The aggregate last/first completion-latency ratio of 0.759 is not evidence of general improvement: it is pulled downward by a large early stall in run 2. Run-level time-series evidence must remain visible beside aggregate window ratios.

## 7. State Conditioning and Independent-Session Study

`EXT-STATE-WRITE-RECOVERY-001` first compared three consecutive idle-start QD16 probes with three post-conditioning probes. Post-write average bandwidth was 147.14 MiB/s versus 122.71 MiB/s at idle-start, but the post-write runs were 159.88, 155.50, and 126.05 MiB/s. The apparent uplift was not stable through the third consecutive probe, showing that fio repeats inside one sequence were not independent state replicates.

`EXT-STATE-REPRO-002` therefore changed the experimental unit to one complete reconnect-start baseline-conditioning-post session. Three sessions preserved a user-confirmed 600-second disconnect, the same physical USB port, a 300-second initial idle, and a 60-second post-conditioning idle.

| Session | Baseline MiB/s | Post-write MiB/s | BW delta | p99 delta | p99.9 delta | Max-latency delta |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 123.85 | 115.96 | -6.37% | +27.62% | +66.19% | +91.78% |
| 2 | 140.87 | 130.17 | -7.59% | +27.34% | +108.97% | +8.13% |
| 3 | 110.34 | 136.08 | +23.33% | -46.24% | -75.00% | -23.27% |

The paired bandwidth direction was mixed: two sessions decreased and one increased. Median bandwidth delta was -6.37%, with a range from -7.59% to +23.33%. The conditioning-uplift hypothesis is therefore `not_reproduced_under_controlled_external_sequence`.

This is not a failed validation activity. `REQ-STATE-REPRO-002` passes because all three planned sessions and paired metrics exist with complete traceability. The performance hypothesis remains not reproduced because its direction was inconsistent. Reconnect-start also remains an external label rather than proof that the SSD entered a common internal state.

## 8. Mixed Read-QoS ABBA/BAAB Decision

The matched ABBA and independent reconnect-start BAAB sessions challenged whether a 70:30 random mix produces repeatable read p99/p99.9 inflation at 4K QD16.

| Session | Comparison | Read BW | Read p99 | Read p99.9 |
|---|---|---:|---:|---:|
| ABBA | B2/B1 | 0.712x | 1.345x | 3.925x |
| BAAB | B2/B1 | 1.224x | 0.910x | 0.724x |

ABBA showed a slower and worse-tail second mixed phase. BAAB reversed all three directions. The repeatable mixed read-tail hypothesis is therefore `not_reproduced_under_controlled_abba_baab_sequences`.

`REQ-MIXED-ABBA-003` and `REQ-MIXED-BAAB-004` pass because their planned phases, manifests, raw JSON, per-direction QoS, and observer evidence exist. A passed evidence requirement does not convert the performance hypothesis into a positive finding.

The completed counterbalanced ratio sweep remains descriptive ratio-by-cycle-by-position mapping. It is not causal confirmation of write-induced read-tail inflation.

See `docs/reports/external_ssd_mixed_abba_baab_result.md`.

## 9. Counterbalanced Mixed-Ratio Mapping

`EXT-MIXED-RATIO-SWEEP-001` placed 90:10, 70:30, and 50:50 once in every cycle and sequence position. All nine phases completed with observed read shares within 0.04 percentage points of request.

| Ratio | Mean total BW MiB/s | BW CV | Mean read p99 ms | Mean read p99.9 ms |
|---|---:|---:|---:|---:|
| 90:10 | 109.215 | 0.583 | 3.013 | 5.688 |
| 70:30 | 129.522 | 0.397 | 1.821 | 3.643 |
| 50:50 | 102.474 | 0.351 | 2.271 | 5.882 |

No monotonic throughput or read-tail penalty appeared as write share increased. The ratio ranges were wide, so the 70:30 session mean advantage is an observation rather than an established DUT characteristic.

Cycle mean total bandwidth rose from 75.124 to 109.744 to 156.343 MiB/s while mean read p99 fell from 3.932 to 2.445 to 0.728 ms. The cycle movement was larger than the ratio separation.

The analyzer flagged Phase 2 late bandwidth rise at 1.553x, a 124.554 ms maximum latency in Phase 2, and a Phase 5 late bandwidth drop to 0.524x. Phase 6 remained low after 60 seconds idle, while Phase 7 was higher after the 300-second cycle boundary. These are externally observed associations, not an identified recovery mechanism.

`REQ-MIXED-RATIO-005` passes because raw evidence, requested mixes, counterbalanced positions, derived CSVs, anomaly rules, and analysis traceability are complete. The completed `EXT-MIXED-RATIO-SWEEP-REPRO-002` follow-on did not reproduce the ratio or phase-transition directions.

See `docs/reports/external_ssd_mixed_ratio_sweep_result.md`.

## 10. Independent Mixed-Ratio Reproduction Verdict

`EXT-MIXED-RATIO-SWEEP-REPRO-002` completed the second nine-phase counterbalanced session with Phase 5 changed from 50:50 to 90:10. The dedicated analyzer compared both sessions automatically.

| Comparison | Session 1 | Session 2 | Reproduced |
|---|---|---|---|
| Total-BW ratio rank | 70:30 > 90:10 > 50:50 | 90:10 > 70:30 > 50:50 | No |
| Cycle BW rank | 3 > 2 > 1 | 1 > 3 > 2 | No |
| Position BW rank | 1 > 2 > 3 | 3 > 2 > 1 | No |
| Phase 5 last/first BW | 0.524x drop | 1.384x rise | No |
| 30-60 s ramp phases | 0 / 9 | 8 / 9 | No |

Session-wide mean total bandwidth changed from 113.737 to 181.231 MiB/s. Mean read p99 changed from 2.368 to 0.635 ms, and mean read p99.9 changed from 5.071 to 1.089 ms.

Transition time is defined as the first five consecutive one-second samples at or above 80% of the last-third mean total bandwidth. Median transition time changed from 1.003 seconds to 44.046 seconds.

`REQ-MIXED-RATIO-REPRO-006` passes because both independent evidence units and their cross-session comparison are complete. The performance verdict is `not_reproduced_across_independent_counterbalanced_sessions`.

See `docs/reports/external_ssd_mixed_ratio_cross_session_result.md`.
## 11. Traceability and Telemetry Status

The traced QD32/QD16 runs and both state protocols contain:

- matching `observer_manifest_pre.json`, `runner_manifest.json`, and `observer_manifest_post.json`
- all planned fio runs with exit code 0
- raw fio JSON and bandwidth/IOPS/latency logs
- parsed sustained and paired-comparison CSVs
- complete child `run_manifest.json` files linked to parent experiment manifests

The integrated manifest now relies on run-specific observer manifests rather than mutable global `results/*/latest` links.

The corrected collector used by the QD16 run confirmed:

- target file `E:\validation\ssd_lab_fio_testfile`
- E: volume `Healthy / OK`
- `SanDisk Extreme SSD`, USB, disk `Healthy / Online`
- unchanged pre/post free-space state for the reused file target

Telemetry interpretation remains Limited because:

- SMART was unavailable or not requested
- storage reliability counters were unavailable through the current Windows access path
- fsutil disk-free query returned a nonzero exit code
- no direct power measurement exists

These limitations are propagated through the observer manifests instead of being reported as complete telemetry coverage.

## 12. Requirement Verdict

| Requirement | Verdict | Evidence / boundary |
|---|---|---|
| `REQ-PERF-001` | Observation | Random-read QD sweep repeat=3 exists; no external specification threshold is defined |
| `REQ-PERF-002` | Observation | Random-write QD sweep repeat=3 exists; no external specification threshold is defined |
| `REQ-QOS-001` | Pass | p99 and p99.9 are reported for QD sweep and sustained runs |
| `REQ-REPRO-001` | Pass | Three QD16 sessions retain per-run CV and cross-session differences |
| `REQ-SUST-001` | Pass | First/middle/last window evidence exists for sustained writes |
| `REQ-SUST-002` | Pass | Matching QD32 write conditions were compared at 120s and 300s |
| `REQ-SUST-003` | Pass | Matching sustained read/write conditions exist at QD16 and QD32 |
| `REQ-STATE-001` | Pass | Baseline, conditioning, and post-write phases are linked with fixed idle intervals |
| `REQ-STATE-REPRO-002` | Pass | Three complete paired sessions preserve the fixed sequence; hypothesis result is not reproduced |
| `REQ-LARGE-WS-001` | Pass | One 32 GiB completion-based sequential write/read sequence preserves raw and time-window evidence |
| `REQ-MIXED-ABBA-003` | Pass | A1/B1/B2/A2 completed; the performance hypothesis was not reproduced |
| `REQ-MIXED-BAAB-004` | Pass | Independent reconnect-start B1/A1/A2/B2 completed; the performance hypothesis was not reproduced |
| `REQ-MIXED-RATIO-005` | Pass | Nine counterbalanced phases and linked ratio/cycle/position/window/anomaly evidence are complete |
| `REQ-MIXED-RATIO-REPRO-006` | Pass | Two complete counterbalanced sessions preserve controls; ratio, cycle, position, Phase 5, and ramp directions were not reproduced |
| `REQ-IDLE-RAMP-007` | Pass | Six phases, all mirrored pairs, transition/QoS CSVs, observer evidence, and integrated traceability are complete; the performance hypothesis was not supported |
| `REQ-BS-008` | Pass | Both nine-phase sessions, counterbalanced placements, variation/QoS summaries, paired comparison, observer evidence, and integrated manifests are complete |
| `REQ-DATA-009` | Pass | Retry1 wrote and verified exactly 4 GiB with CRC32C and fio error 0 in both phases |
| `REQ-HOST-OBS-010` | Limited | Both phase collectors ran, but all 23 logical-disk samples were zero while fio was active |
| `REQ-ENV-001` | Pass for traced runs | Pre/post environment collectors are linked by run ID |
| `REQ-TEL-001` | Limited | Target metadata is correct; SMART, reliability counters, and fsutil remain limited |
| `REQ-OBS-001` | Pass for traced runs | Pre observer, runner, and post observer are linked |
| `REQ-TRACE-001` | Pass for traced runs | Integrated manifests link conditions and run-specific evidence |
| `REQ-LIMIT-001` | Pass | USB, Windows, exFAT, file-target, telemetry, and root-cause limits are explicit |

## 13. Limitations

- Most sustained studies use a 512 MiB file; later sequential and mixed studies use a dedicated 32 GiB file. Neither establishes full-drive or enterprise steady-state behavior.
- The three state-reproducibility sessions occurred on one host and date; reconnect-start does not guarantee a common internal SSD state.
- USB bridge, enclosure, port, host controller, Windows, exFAT, and fio file-target effects are combined.
- The QD32 evidence-complete run predates the corrected target-aware telemetry collector.
- Exact DUT model, enclosure/adapter, and host port remain to be confirmed.
- No direct power measurement or internal firmware/NAND/FTL/GC trace is available.
- Hard performance pass/fail thresholds require an external requirement or established baseline.

## 14. Current Verdict

The lab now demonstrates both measurement and evidence engineering: controlled fio conditions, repeated raw data, three-session QD16 comparison, tail-latency anomaly retention, target-aware telemetry limitations, separate runner/observer roles, and integrated traceability.

The QD32 300s late-run degradation observed in the first session was not reproduced in the traced session. The stronger conclusion is that session state materially affects black-box results and that rare multi-second stalls must be reviewed separately from p99/p99.9.

At QD16 120s, the lower throughput level was reproduced across two consecutive sessions, but the severe p99.9 inflation was not. Throughput state and tail-latency state must therefore be tracked as separate validation dimensions.

The later paired state study improved the experimental unit from consecutive fio repeats to complete reconnect-start sessions. Its mixed -6.37%, -7.59%, and +23.33% bandwidth deltas showed that a conditioning uplift was not reproducible under the controlled external sequence. The strongest conclusion is session-level black-box variability, not a deterministic internal mechanism.

The subsequent ABBA/BAAB study reached the same kind of disciplined negative result: the second mixed phase degraded in ABBA but improved in BAAB. Repeatable 70:30 read-tail inflation was not reproduced, so the ratio sweep was explicitly exploratory and counterbalanced rather than framed as causal confirmation.

The independent Session 2 did not reproduce Session 1 ratio, cycle, position, or Phase 5 directions. Session 2 instead showed a systematic 37-53 second ramp in nearly every phase. The automated cross-session verdict is `not_reproduced_across_independent_counterbalanced_sessions`; the next useful question is idle-duration sensitivity, not a third full ratio sweep.

`EXT-IDLE-RAMP-001` completed that question. The prior 37-53 second ramp did not recur in any phase, and all three mirrored pairs consistently classified as no ramp. Average bandwidth still differed by +14.9% for the 0-second pair and +55.8% for the 300-second pair, so ramp classification consistency did not imply performance reproducibility. The verdict is `no_clear_idle_duration_association`; pre-probe idle length did not explain the session-level state variation.

The controlled block-size study then closed the final baseline matrix gap with independent counterbalanced read and write sessions. Bandwidth repeatability was strong and aggregate order effects were small. At QD32, 64K reached the observed throughput plateau; moving to 1M provided no bandwidth gain while increasing p99 latency by 13.77x for read and 15.69x for write. This is a condition-specific throughput knee, not a universal optimal block size.

The performance-characterization phase is mature and the first correctness MVP is complete: the 4 GiB CRC32C file-target path passed. Synchronized logical-disk observation was exercised but remained Limited because it captured no nonzero workload signal. The roadmap now moves to a compact requirement-based regression profile rather than another broad parameter sweep. Korean portfolio material is deferred until explicitly requested.

Portfolio statement:

> I treated an external SSD as a black-box DUT, translated validation questions into controlled fio conditions, improved the experimental unit when consecutive repeats proved dependent, preserved paired raw evidence across three reconnect-start sessions, and separated requirement completion from a performance hypothesis that was not reproduced.
