# External SSD Product Validation Report

Status: QD sweep repeat=3 and sustained write 120s repeat=3 completed.

## 1. Scope

This report treats the external SSD as a black-box DUT and evaluates observable product behavior through fio-based file-target testing.

It does not attempt to inspect or prove internal FTL/GC behavior.

Related setup documents:

- `docs/reports/external_ssd_dut_profile.md`
- `docs/reports/external_ssd_requirement_matrix.md`
- `docs/reports/external_ssd_execution_runbook.md`
- `configs/external_ssd_validation_matrix.yaml`

## 2. DUT Summary

| Field | Value |
|---|---|
| DUT label | `external_ssd_dut_01` |
| Model | TBD |
| Connection | External SSD over USB path |
| File system | exFAT |
| Test path | `E:\validation\ssd_lab_fio_testfile` |
| Environment snapshot | TBD |
| Telemetry snapshot | TBD |

## 3. Test Matrix Summary

| Test case | Workload | Runtime | Repeats | Status |
|---|---|---:|---:|---|
| `EXT-QD-SMOKE` | randread/randwrite 4k QD 1/4/16/32 | 30s | 1 | Done |
| `EXT-PERF-RR-QD-SWEEP` | randread 4k QD 1/4/16/32 | 30s | 3 | Done |
| `EXT-PERF-RW-QD-SWEEP` | randwrite 4k QD 1/4/16/32 | 30s | 3 | Done |
| `EXT-SUST-WRITE-120S` | randwrite 4k QD16 | 120s | 3 | Done |
| `EXT-SUST-WRITE-300S` | randwrite 4k QD16 | 300s | 3 | TBD |
| `EXT-SUST-READ-120S` | randread 4k QD16 | 120s | 3 | TBD |

## 4. Result Summary

The first external SSD QD sweep smoke ran successfully against `E:\validation\ssd_lab_fio_testfile` and produced 8 JSON files.

Evidence:

- `results/external_ssd/qd_sweep_smoke/`
- `results/external_ssd_qd_smoke_summary.csv`
- `results/external_ssd_qd_smoke_grouped.csv`

| Workload | QD | BW MiB/s | IOPS | p99 us | p99.9 us | Note |
|---|---:|---:|---:|---:|---:|---|
| rand_read | 1 | 17.24 | 4,414.39 | 337.92 | 708.61 | Smoke only |
| rand_read | 4 | 69.23 | 17,722.44 | 374.78 | 514.05 | Smoke only |
| rand_read | 16 | 205.12 | 52,509.65 | 667.65 | 921.60 | Smoke only |
| rand_read | 32 | 255.86 | 65,500.95 | 1,019.90 | 1,400.83 | Smoke only |
| rand_write | 1 | 63.41 | 16,232.26 | 92.67 | 156.67 | Smoke only |
| rand_write | 4 | 177.19 | 45,360.22 | 110.08 | 203.78 | Smoke only |
| rand_write | 16 | 195.30 | 49,996.87 | 692.22 | 1,138.69 | Smoke only |
| rand_write | 32 | 186.79 | 47,818.94 | 1,011.71 | 1,581.06 | Smoke only |


### Repeat=3 QD Sweep Result

The repeat=3 run produced 24 JSON files under `results/external_ssd/qd_sweep_repeat3/`. All checked jobs reported `error: 0` and targeted `E:\validation\ssd_lab_fio_testfile`.

Evidence:

- `results/external_ssd/qd_sweep_repeat3/`
- `results/external_ssd_qd_repeat3_summary.csv`
- `results/external_ssd_qd_repeat3_grouped.csv`

| Workload | QD | Runs | Avg BW MiB/s | BW CV | Avg IOPS | IOPS CV | Avg p99 us | p99 CV | Avg p99.9 us | p99.9 CV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rand_read | 1 | 3 | 15.46 | 0.016 | 3,959.11 | 0.016 | 350.21 | 0.031 | 547.50 | 0.023 |
| rand_read | 4 | 3 | 64.00 | 0.004 | 16,382.92 | 0.004 | 389.80 | 0.006 | 531.80 | 0.022 |
| rand_read | 16 | 3 | 197.00 | 0.006 | 50,430.60 | 0.006 | 703.15 | 0.007 | 976.21 | 0.005 |
| rand_read | 32 | 3 | 257.65 | 0.002 | 65,959.01 | 0.002 | 1,144.15 | 0.008 | 1,591.98 | 0.006 |
| rand_write | 1 | 3 | 62.71 | 0.008 | 16,053.86 | 0.008 | 92.33 | 0.034 | 142.34 | 0.025 |
| rand_write | 4 | 3 | 187.98 | 0.052 | 48,123.72 | 0.052 | 129.02 | 0.187 | 242.35 | 0.166 |
| rand_write | 16 | 3 | 192.23 | 0.014 | 49,210.83 | 0.014 | 398.00 | 0.016 | 583.00 | 0.032 |
| rand_write | 32 | 3 | 193.01 | 0.021 | 49,410.50 | 0.021 | 1,067.69 | 0.431 | 1,600.17 | 0.456 |

Repeat=3 interpretation:

- Random read scaled clearly with QD and stayed stable across repeats. IOPS CV stayed at or below 0.016, and p99 CV stayed at or below 0.031.
- Random write throughput improved from QD1 to QD16/QD32, but QD32 did not materially improve average IOPS over QD16.
- Random write QD32 showed the weakest QoS stability: p99 CV was 0.431 and p99.9 CV was 0.456.
- This supports the validation point that a high-throughput condition can still be a risky QoS candidate.

## 5. QoS Review

Questions:

- Which condition has the highest p99 latency?
- Which condition has the highest p99.9 latency?
- Does the highest-throughput condition also have acceptable tail latency?
- Which condition has the largest run-to-run variation?

Evidence:

- `results/external_ssd_qd_smoke_grouped.csv`
- `results/external_ssd_qd_repeat3_grouped.csv`

## 6. Sustained Workload Review

The first external SSD sustained run used the QD16 random-write condition selected from the QD sweep as a reasonable high-throughput condition with better tail stability than QD32.

Evidence:

- `results/external_ssd/sustained_rand_write_120s_qd16_repeat3/`
- `results/external_ssd_sustained_summary.csv`
- `results/external_ssd_sustained_timeseries.csv`
- `results/external_ssd_sustained_window_summary.csv`
- `results/external_ssd_sustained_repeatability.csv`

Aggregate repeat=3 result:

| Workload | Runtime | QD | Runs | Avg BW MiB/s | BW CV | Avg IOPS | IOPS CV | Avg p99 us | p99 CV | Avg p99.9 us | p99.9 CV | Max latency CV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| randwrite 4k | 120s | 16 | 3 | 162.96 | 0.044 | 41,716.65 | 0.044 | 516.10 | 0.062 | 735.91 | 0.084 | 0.770 |

Per-run aggregate result:

| Run | BW MiB/s | IOPS | p99 us | p99.9 us | Max us |
|---:|---:|---:|---:|---:|---:|
| 1 | 154.83 | 39,636.53 | 552.96 | 806.91 | 34,681.69 |
| 2 | 166.14 | 42,532.98 | 497.66 | 692.22 | 2,981.83 |
| 3 | 167.89 | 42,980.43 | 497.66 | 708.61 | 26,461.35 |

Window-level observation:

| Metric | Mean ratio |
|---|---:|
| Last-third IOPS / first-third IOPS | 1.058 |
| Last-third avg clat / first-third avg clat | 0.949 |

Interpretation:

- The 120s QD16 sustained write run did not show a throughput drop across the run. The last-third IOPS was slightly higher than the first-third average.
- Average completion latency also did not worsen across the run; last-third average clat was about 0.95x of first-third average clat.
- Compared with the short QD16 repeat=3 sweep, sustained write average IOPS was lower, so runtime and logging context matter.
- Max latency remained outlier-sensitive. Runs 1 and 3 had much larger max-latency values than run 2, so max latency should be reviewed separately from p99/p99.9.
- This is still black-box file-target behavior through USB/exFAT/Windows, not direct evidence of internal SSD GC or FTL behavior.

## 7. Telemetry Observation

Record what was collected:

| Source | Status | Note |
|---|---|---|
| Environment snapshot | TBD | TBD |
| Storage telemetry snapshot | TBD | TBD |
| SMART / device health | TBD | TBD |
| Temperature | TBD | TBD |
| Power measurement | Not available unless external measurement is added | Do not claim direct power validation without measurement equipment |

## 8. Anomaly Review

Use this structure for any p99.9 spike, max-latency outlier, or throughput drop.

```text
Symptom:

Reproduction condition:

Compared against:

Evidence available:

Possible causes:

Evidence not available:

Next debug step:
```

## 9. Requirement Verdict

| Requirement | Verdict | Evidence |
|---|---|---|
| REQ-PERF-001 | Pass | randread QD 1/4/16/32 repeat=3 completed |
| REQ-PERF-002 | Pass | randwrite QD 1/4/16/32 repeat=3 completed |
| REQ-QOS-001 | Pass | p99 and p99.9 reported for QD sweep and sustained runs |
| REQ-REPRO-001 | Pass | Each QD condition ran 3 repeats and CV was reported |
| REQ-SUST-001 | Pass | 120s randwrite QD16 repeat=3 window summary generated |
| REQ-SUST-002 | TBD | TBD |
| REQ-SUST-003 | TBD | TBD |
| REQ-ENV-001 | TBD | TBD |
| REQ-TEL-001 | TBD | TBD |
| REQ-LIMIT-001 | Pass for smoke | Report states black-box and USB/filesystem limitations |

## 10. Limitations

- External SSD results include USB bridge, enclosure, port, host controller, OS, filesystem, and fio file-target effects.
- This report is black-box validation evidence, not internal FTL/GC proof.
- Direct power validation requires measurement equipment. Without it, only power-aware or thermal/telemetry observations should be claimed.
- Hard pass/fail thresholds should be added only after a baseline is established or a requirement source is defined.

## 11. Portfolio Summary

TBD after results are available.

Suggested shape:

> I treated an external SSD as a black-box DUT, defined product-like performance requirements, executed fio-based workloads, parsed JSON results into CSV, reviewed p99/p99.9 and sustained behavior, and documented verdicts with clear interpretation limits.
