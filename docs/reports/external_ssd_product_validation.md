# External SSD Product Validation Report

Status: QD sweep, sustained QD16/QD32 studies, one state-recovery sequence, and three independently initiated paired state-reproducibility sessions completed. The state studies retain parent/child manifests, matching observer/runner evidence, parsed CSVs, and explicit hypothesis verdicts.

## 1. Scope

This report treats the external SSD as a black-box DUT and evaluates observable product behavior through fio file-target testing.

It covers controlled conditions, repeated execution, p99/p99.9 latency, sustained time-window behavior, cross-session repeatability, evidence traceability, and interpretation limits. It does not inspect or prove internal FTL/GC behavior.

Related evidence:

- `docs/reports/external_ssd_dut_profile.md`
- `docs/reports/external_ssd_requirement_matrix.md`
- `docs/reports/external_ssd_execution_runbook.md`
- `configs/external_ssd_validation_matrix.yaml`
- `results/external_ssd/`
- `results/external_ssd_sustained_*.csv`
- `results/external_ssd_state_repro_pairs.csv`
- `results/external_ssd_state_repro_study_summary.csv`

## 2. DUT and Environment

| Field | Value |
|---|---|
| DUT label | `external_ssd_dut_01` |
| Vendor / family | SanDisk Extreme Portable SSD; exact model pending confirmation |
| Connection | External SSD over USB path |
| File system | exFAT |
| Test target | `E:\validation\ssd_lab_fio_testfile` |
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

The analyzer currently includes 40 sustained fio JSON jobs. All report `error: 0`, and each result set contains the expected time-series logs.

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

## 8. Traceability and Telemetry Status

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

## 9. Requirement Verdict

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
| `REQ-ENV-001` | Pass for traced runs | Pre/post environment collectors are linked by run ID |
| `REQ-TEL-001` | Limited | Target metadata is correct; SMART, reliability counters, and fsutil remain limited |
| `REQ-OBS-001` | Pass for traced runs | Pre observer, runner, and post observer are linked |
| `REQ-TRACE-001` | Pass for traced runs | Integrated manifests link conditions and run-specific evidence |
| `REQ-LIMIT-001` | Pass | USB, Windows, exFAT, file-target, telemetry, and root-cause limits are explicit |

## 10. Limitations

- The test file is 512 MiB, so results do not establish large-working-set, full-drive, or enterprise steady-state behavior.
- The three state-reproducibility sessions occurred on one host and date; reconnect-start does not guarantee a common internal SSD state.
- USB bridge, enclosure, port, host controller, Windows, exFAT, and fio file-target effects are combined.
- The QD32 evidence-complete run predates the corrected target-aware telemetry collector.
- Exact DUT model, enclosure/adapter, and host port remain to be confirmed.
- No direct power measurement or internal firmware/NAND/FTL/GC trace is available.
- Hard performance pass/fail thresholds require an external requirement or established baseline.

## 11. Current Verdict

The lab now demonstrates both measurement and evidence engineering: controlled fio conditions, repeated raw data, three-session QD16 comparison, tail-latency anomaly retention, target-aware telemetry limitations, separate runner/observer roles, and integrated traceability.

The QD32 300s late-run degradation observed in the first session was not reproduced in the traced session. The stronger conclusion is that session state materially affects black-box results and that rare multi-second stalls must be reviewed separately from p99/p99.9.

At QD16 120s, the lower throughput level was reproduced across two consecutive sessions, but the severe p99.9 inflation was not. Throughput state and tail-latency state must therefore be tracked as separate validation dimensions.

The later paired state study improved the experimental unit from consecutive fio repeats to complete reconnect-start sessions. Its mixed -6.37%, -7.59%, and +23.33% bandwidth deltas showed that a conditioning uplift was not reproducible under the controlled external sequence. The strongest conclusion is session-level black-box variability, not a deterministic internal mechanism.

Portfolio statement:

> I treated an external SSD as a black-box DUT, translated validation questions into controlled fio conditions, improved the experimental unit when consecutive repeats proved dependent, preserved paired raw evidence across three reconnect-start sessions, and separated requirement completion from a performance hypothesis that was not reproduced.
