# External SSD Product Validation Report

Status: QD sweep repeat=3, sustained read/write QD16/QD32 120s repeat=3, and two sustained random-write QD32 300s repeat=3 sessions completed. The 2026-07-21 QD32 300s run is the first result with matching pre-observer, runner, and post-observer evidence under one run ID.

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

## 2. DUT and Environment

| Field | Value |
|---|---|
| DUT label | `external_ssd_dut_01` |
| Vendor / family | SanDisk Extreme Portable SSD; exact model pending confirmation |
| Connection | External SSD over USB path |
| File system | exFAT |
| Test target | `E:\validation\ssd_lab_fio_testfile` |
| fio version | `fio-3.42` |
| Evidence-complete run ID | `sustained_rand_write_300s_qd32_trace_repeat3_20260721` |

The evidence-complete run has pre/post environment and telemetry collector outputs linked through observer manifests. The collector used during that run still recorded its legacy D: test file in `testfile_info.txt`, so device telemetry for that run remains Limited even though execution traceability is complete. The collector has since been corrected to derive the target file and drive from `SSD_LAB_EXTERNAL_TESTFILE`.

## 3. Execution Coverage

| Test case | Condition | Repeats | Status |
|---|---|---:|---|
| `EXT-QD-SMOKE` | 4K randread/randwrite, QD 1/4/16/32, 30s | 1 | Complete |
| `EXT-PERF-RR-QD-SWEEP` | 4K randread, QD 1/4/16/32, 30s | 3 | Complete |
| `EXT-PERF-RW-QD-SWEEP` | 4K randwrite, QD 1/4/16/32, 30s | 3 | Complete |
| `EXT-SUST-WRITE-120S` | 4K randwrite, QD16, 120s | 3 + 3 | Two sessions complete; second session lacks pre-observer |
| `EXT-SUST-READ-120S` | 4K randread, QD16, 120s | 3 | Complete |
| `EXT-SUST-READ-QD32-120S` | 4K randread, QD32, 120s | 3 | Complete |
| `EXT-SUST-WRITE-QD32-120S` | 4K randwrite, QD32, 120s | 3 | Complete |
| `EXT-SUST-WRITE-QD32-300S` | 4K randwrite, QD32, 300s | 3 + 3 | Two sessions complete; latest execution trace complete |

The analyzer currently includes 21 sustained fio JSON jobs. All report `error: 0`, and each result set contains the expected time-series logs.

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
| randwrite 120s QD32 | 141.73 | 0.051 | 36,283 | 1,226.07 | 2,124.46 | 0.974 | 1.016 |
| randwrite 300s QD32, original | 138.74 | 0.065 | 35,517 | 1,329.83 | 3,249.49 | 0.910 | 1.116 |
| randwrite 300s QD32, traced | 147.90 | 0.010 | 37,862 | 1,015.81 | 1,717.59 | 1.014 | 0.759 |

The second QD16 session was materially slower and had much worse tail latency than the original QD16 session. This confirms that a single repeat group is insufficient to describe cross-session behavior.

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

## 7. Traceability and Telemetry Status

The traced 300s QD32 run contains:

- `observer_manifest_pre.json`: complete execution record
- `runner_manifest.json`: 3 runs, all exit code 0
- `observer_manifest_post.json`: complete execution record
- raw fio JSON and bandwidth/IOPS/latency logs
- parsed summary, time-series, window, and repeatability CSVs
- integrated `run_manifest.json`: `complete`

The integrated manifest now relies on run-specific observer manifests rather than mutable global `results/*/latest` links.

Telemetry interpretation remains Limited for the completed run because:

- its legacy collector recorded the wrong test-file metadata path
- SMART was unavailable or not requested
- storage reliability counters were unavailable through the current Windows access path
- no direct power measurement exists

The corrected collector now records `target_file`, `target_drive`, `status`, and explicit `limitations`. A future run will propagate those limitations through the observer manifest instead of reporting collector completion as full telemetry coverage.

## 8. Requirement Verdict

| Requirement | Verdict | Evidence / boundary |
|---|---|---|
| `REQ-PERF-001` | Observation | Random-read QD sweep repeat=3 exists; no external specification threshold is defined |
| `REQ-PERF-002` | Observation | Random-write QD sweep repeat=3 exists; no external specification threshold is defined |
| `REQ-QOS-001` | Pass | p99 and p99.9 are reported for QD sweep and sustained runs |
| `REQ-REPRO-001` | Pass | Three repeats and CV are reported; cross-session differences are retained |
| `REQ-SUST-001` | Pass | First/middle/last window evidence exists for sustained writes |
| `REQ-SUST-002` | Pass | Matching QD32 write conditions were compared at 120s and 300s |
| `REQ-SUST-003` | Pass | Matching sustained read/write conditions exist at QD16 and QD32 |
| `REQ-ENV-001` | Pass for traced run | Pre/post environment collectors are linked by run ID |
| `REQ-TEL-001` | Limited | Collector ran, but target metadata and device-level counters were incomplete |
| `REQ-OBS-001` | Pass for traced run | Pre observer, runner, and post observer are linked |
| `REQ-TRACE-001` | Pass for traced run | Integrated manifest links conditions and run-specific evidence |
| `REQ-LIMIT-001` | Pass | USB, Windows, exFAT, file-target, telemetry, and root-cause limits are explicit |

## 9. Limitations

- The test file is 512 MiB, so results do not establish full-drive or enterprise steady-state behavior.
- USB bridge, enclosure, port, host controller, Windows, exFAT, and fio file-target effects are combined.
- The evidence-complete run predates the corrected target-aware telemetry collector.
- Exact DUT model, enclosure/adapter, and host port remain to be confirmed.
- No direct power measurement or internal firmware/NAND/FTL/GC trace is available.
- Hard performance pass/fail thresholds require an external requirement or established baseline.

## 10. Current Verdict

The lab now demonstrates both measurement and evidence engineering: controlled fio conditions, repeated raw data, cross-session comparison, tail-latency anomaly retention, separate runner/observer roles, and integrated traceability.

The QD32 300s late-run degradation observed in the first session was not reproduced in the traced session. The stronger conclusion is that session state materially affects black-box results and that rare multi-second stalls must be reviewed separately from p99/p99.9.

Portfolio statement:

> I treated an external SSD as a black-box DUT, translated validation questions into controlled fio conditions, preserved raw JSON and time-series evidence, compared both within-session and cross-session repeatability, and connected requirements, execution roles, artifacts, verdicts, anomalies, and limitations through run manifests.
