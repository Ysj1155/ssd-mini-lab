# External SSD Product Validation Report

Status: QD sweep repeat=3 and sustained read/write QD16/QD32 120s repeat=3 completed. Sustained random write QD32 300s repeat=3 also completed and analyzed. Historical sustained runs have integrated manifests but are `limited` because they predate runner/observer evidence collection.

## 1. Scope

This report treats the external SSD as a black-box DUT and evaluates observable product behavior through fio file-target testing.

It covers condition control, repeated execution, p99/p99.9 latency, sustained time-window behavior, evidence traceability, and interpretation limits. It does not inspect or prove internal FTL/GC behavior.

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
| fio version in sustained JSON | `fio-3.42` |
| Environment snapshot | `results/env/latest/manifest.json`, collected 2026-06-08 |
| Telemetry snapshot | `results/telemetry/latest/manifest.json`, collected 2026-06-08 |

The available environment and telemetry snapshots are older than the July sustained runs. They document tooling capability but are not contemporaneous pre/post evidence for those runs.

## 3. Execution Coverage

| Test case | Condition | Repeats | Status |
|---|---|---:|---|
| `EXT-QD-SMOKE` | 4K randread/randwrite, QD 1/4/16/32, 30s | 1 | Complete |
| `EXT-PERF-RR-QD-SWEEP` | 4K randread, QD 1/4/16/32, 30s | 3 | Complete |
| `EXT-PERF-RW-QD-SWEEP` | 4K randwrite, QD 1/4/16/32, 30s | 3 | Complete |
| `EXT-SUST-WRITE-120S` | 4K randwrite, QD16, 120s | 3 | Complete |
| `EXT-SUST-READ-120S` | 4K randread, QD16, 120s | 3 | Complete |
| `EXT-SUST-READ-QD32-120S` | 4K randread, QD32, 120s | 3 | Complete |
| `EXT-SUST-WRITE-QD32-120S` | 4K randwrite, QD32, 120s | 3 | Complete |
| `EXT-SUST-WRITE-QD32-300S` | 4K randwrite, QD32, 300s | 3 | Complete, traceability limited |
| `EXT-SUST-WRITE-300S` | 4K randwrite, QD16, 300s | 3 | Deferred; not needed for the current QD32 runtime comparison |

All 15 sustained fio JSON jobs included in the current analyzer output report `error: 0`. The completed sustained result sets contain matching time-series logs.

## 4. QD Sweep Observation

The repeat=3 QD sweep produced 24 JSON files. The checked results targeted `E:\validation\ssd_lab_fio_testfile`.

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

Random read scaled with QD and remained repeatable. Random write throughput saturated around QD16, while QD32 added no meaningful average throughput and showed the weakest short-run tail-latency repeatability. That made QD32 random write the sustained QoS risk candidate.

## 5. Sustained Result Summary

| Result set | Avg BW MiB/s | BW CV | Avg IOPS | Avg p99 us | Avg p99.9 us | Last/first IOPS | Last/first avg clat |
|---|---:|---:|---:|---:|---:|---:|---:|
| randread 120s QD16 | 170.19 | 0.058 | 43,570 | 749.57 | 1,798.14 | 1.038 | 1.003 |
| randread 120s QD32 | 235.12 | 0.078 | 60,192 | 1,095.00 | 1,591.98 | 0.979 | 1.026 |
| randwrite 120s QD16 | 162.96 | 0.044 | 41,717 | 516.10 | 735.91 | 1.059 | 0.950 |
| randwrite 120s QD32 | 141.73 | 0.051 | 36,283 | 1,226.07 | 2,124.46 | 0.974 | 1.016 |
| randwrite 300s QD32 | 138.74 | 0.065 | 35,517 | 1,329.83 | 3,249.49 | 0.910 | 1.116 |

The 120s QD16 write condition was the strongest sustained write condition in this set: it delivered higher throughput than QD32 and had lower tail latency. QD32 therefore represents queueing and QoS stress rather than a useful performance gain.

## 6. QD32 Write Runtime Comparison

| Metric | 120s | 300s | Observation |
|---|---:|---:|---|
| Avg BW MiB/s | 141.73 | 138.74 | 2.1% lower at 300s |
| Avg IOPS | 36,283 | 35,517 | 2.1% lower at 300s |
| Avg p99 us | 1,226.07 | 1,329.83 | 8.5% higher at 300s |
| Avg p99.9 us | 2,124.46 | 3,249.49 | 53.0% higher at 300s |
| Last/first IOPS | 0.974 | 0.910 | Larger late-run decline at 300s |
| Last/first avg clat | 1.016 | 1.116 | Larger late-run latency increase at 300s |

The 300s run strengthens the black-box observation that longer QD32 write stress worsens tail behavior even though average bandwidth changes only modestly. The three 300s runs were not identical: run 1 averaged 128.43 MiB/s, while runs 2 and 3 averaged 142.50 and 145.29 MiB/s. Run-level and time-window evidence should therefore remain visible beside the aggregate.

This pattern is compatible with a device/path reaching a less stable sustained state, but the current evidence cannot isolate SSD firmware, USB transport, host scheduling, filesystem behavior, or thermal effects as the cause.

## 7. Traceability and Telemetry Status

Each sustained result directory now has an integrated `run_manifest.json` linking observed fio conditions, raw JSON/logs, requirements, DUT documentation, and parsed CSVs.

The existing sustained runs were executed before separate runner/observer manifests were introduced. Their current manifests correctly report:

- `status: limited`
- missing `runner_manifest.json`
- missing `observer_manifest_pre.json` and `observer_manifest_post.json`
- an explicit `missing_execution_evidence` anomaly

This limitation does not invalidate the fio measurements. It limits claims about execution provenance and contemporaneous environment/telemetry correlation.

The next runbook procedure fixes this gap by requiring observer pre, runner, observer post, analysis, and integrated manifest generation under one run ID.

Direct power validation remains out of scope without external measurement equipment. SMART and temperature are reported only when the USB path and available tools expose them.

## 8. Requirement Verdict

| Requirement | Verdict | Evidence / boundary |
|---|---|---|
| `REQ-PERF-001` | Observation | Random-read QD sweep repeat=3 is present; no external specification threshold is defined |
| `REQ-PERF-002` | Observation | Random-write QD sweep repeat=3 is present; no external specification threshold is defined |
| `REQ-QOS-001` | Pass | p99 and p99.9 are reported for QD sweep and sustained runs |
| `REQ-REPRO-001` | Pass | Three repeats and CV are reported for major conditions |
| `REQ-SUST-001` | Pass | First/middle/last window evidence exists for sustained writes |
| `REQ-SUST-002` | Pass | Matching QD32 write conditions were compared at 120s and 300s |
| `REQ-SUST-003` | Pass | Matching sustained read/write conditions are available at QD16 and QD32 |
| `REQ-ENV-001` | Limited | Environment snapshot exists but is not contemporaneous with the sustained runs |
| `REQ-TEL-001` | Limited | Read-only telemetry snapshot exists but is not linked as pre/post run evidence |
| `REQ-OBS-001` | Limited | Historical runs lack separate runner and observer manifests |
| `REQ-TRACE-001` | Limited | Integrated manifests exist and explicitly identify execution-evidence gaps |
| `REQ-LIMIT-001` | Pass | USB, Windows, exFAT, file-target, and internal-root-cause limits are explicit |

## 9. Limitations

- The test file is 512 MiB, so results do not establish full-drive or steady-state enterprise behavior.
- The USB bridge, enclosure, port, host controller, Windows, exFAT, and fio file-target path all contribute to the observed result.
- Historical runs lack contemporaneous pre/post observer evidence.
- Exact DUT model, enclosure/adapter, and host port remain to be confirmed before public portfolio wording.
- No direct power measurement is available.
- No internal firmware, NAND, FTL, or GC trace is available.
- Hard pass/fail performance thresholds require an external requirement or a deliberately established baseline.

## 10. Current Verdict and Next Step

The lab has demonstrated a repeatable black-box validation workflow and identified QD32 random write as a QoS stress condition: longer runtime produced modestly lower average performance, materially higher p99.9 latency, and worse late-run window ratios.

The next experiment is an evidence-complete confirmation of the 300s QD32 random-write condition using a new run ID and the fixed runner/observer sequence. Its purpose is to confirm the observation across sessions while proving that DUT, conditions, execution, telemetry limitations, raw data, and analysis can be traced as one run.

Portfolio statement:

> I treated an external SSD as a black-box DUT, translated validation questions into controlled fio conditions, preserved raw JSON and time-series evidence, analyzed repeatability and p99/p99.9 behavior, and connected requirements, execution roles, artifacts, verdicts, and limitations through run manifests.
