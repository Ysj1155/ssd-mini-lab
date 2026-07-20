# External SSD Requirement Matrix

This document turns product-like validation expectations into testable requirements.

The values below are intentionally framed as tracking and review requirements first. Hard pass/fail thresholds can be added after a baseline is established for the actual external SSD DUT.

## Requirements

| ID | Requirement | Evidence | Initial verdict rule |
|---|---|---|---|
| REQ-PERF-001 | 4K random read performance shall be measured across QD 1/4/16/32. | fio JSON, parsed CSV, QD plot | Observation until baseline is established |
| REQ-PERF-002 | 4K random write performance shall be measured across QD 1/4/16/32. | fio JSON, parsed CSV, QD plot | Observation until baseline is established |
| REQ-QOS-001 | p99 and p99.9 latency shall be reported separately from average latency. | summary CSV, QoS plot | Pass if both metrics are present |
| REQ-REPRO-001 | Major conditions shall run at least 3 repeats and report CV or run-to-run variation. | repeatability CSV | Pass if repeat count and variation are reported |
| REQ-SUST-001 | Sustained random-write behavior shall be reviewed over time windows. | time-series CSV, sustained plots | Pass if first/middle/last windows are available |
| REQ-SUST-002 | Longer write runtime shall be compared against shorter write runtime. | result-set comparison CSV | Pass if 300s vs 120s ratio is reported |
| REQ-SUST-003 | Sustained read behavior shall be compared against matching sustained write behavior. | workload comparison CSV | Pass if matching read/write conditions are compared |
| REQ-ENV-001 | Each validation run shall include environment and path context. | env snapshot, DUT profile | Pass if snapshot and DUT profile are linked |
| REQ-TEL-001 | Telemetry shall be collected when available without destructive access. | telemetry snapshot | Pass if collected, Limited if permissions/tooling block device-level data |
| REQ-LIMIT-001 | The report shall state what the evidence cannot prove. | final report limitation section | Pass if interpretation boundary is explicit |

## Requirement-to-Test Mapping

| Test case | Requirements |
|---|---|
| `EXT-PERF-RR-QD-SWEEP` | REQ-PERF-001, REQ-QOS-001, REQ-REPRO-001 |
| `EXT-PERF-RW-QD-SWEEP` | REQ-PERF-002, REQ-QOS-001, REQ-REPRO-001 |
| `EXT-SUST-WRITE-120S` | REQ-SUST-001, REQ-QOS-001, REQ-REPRO-001 |
| `EXT-SUST-WRITE-300S` | REQ-SUST-001, REQ-SUST-002, REQ-QOS-001, REQ-REPRO-001 |
| `EXT-SUST-READ-120S` | REQ-SUST-003, REQ-QOS-001, REQ-REPRO-001 |

## Verdict Vocabulary

Use conservative verdict wording:

- `Pass`: required evidence exists and meets the defined rule.
- `Observation`: evidence exists, but no mature threshold has been defined yet.
- `Limited`: the test ran, but environment, permissions, or tooling limited interpretation.
- `Blocked`: the test could not run or critical evidence is missing.

Avoid claiming internal SSD root cause unless device-level or firmware-level evidence exists.
