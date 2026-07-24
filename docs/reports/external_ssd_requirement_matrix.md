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
| REQ-STATE-001 | QD16 write behavior shall be compared before and after a fixed QD32 write-conditioning sequence. | experiment manifest, fio JSON, summary and repeatability CSVs | Pass if both probes and the conditioning phase are linked with fixed idle intervals |
| REQ-STATE-REPRO-002 | The complete baseline-conditioning-post sequence shall be repeated across three independently initiated sessions and evaluated with paired deltas. | session manifests, fio JSON, paired comparison CSV | Pass if three complete sessions preserve the fixed sequence and paired metrics |
| REQ-ENV-001 | Each validation run shall include environment and path context. | env snapshot, DUT profile | Pass if snapshot and DUT profile are linked |
| REQ-TEL-001 | Telemetry shall be collected when available without destructive access. | telemetry snapshot | Pass if collected, Limited if permissions/tooling block device-level data |
| REQ-OBS-001 | fio execution and read-only observation shall be recorded as separate evidence producers. | `runner_manifest.json`, `observer_manifest_<phase>.json` | Pass if both are linked, Limited if one side is missing with an explicit anomaly |
| REQ-TRACE-001 | Each sustained validation result set shall link DUT, requirements, test conditions, raw artifacts, parsed CSVs, and environment evidence. | `run_manifest.json` | Pass if manifest exists and status is complete or limited with explicit anomalies |
| REQ-LIMIT-001 | The report shall state what the evidence cannot prove. | final report limitation section | Pass if interpretation boundary is explicit |

## Requirement-to-Test Mapping

| Test case | Requirements |
|---|---|
| `EXT-PERF-RR-QD-SWEEP` | REQ-PERF-001, REQ-QOS-001, REQ-REPRO-001 |
| `EXT-PERF-RW-QD-SWEEP` | REQ-PERF-002, REQ-QOS-001, REQ-REPRO-001 |
| `EXT-SUST-WRITE-120S` | REQ-SUST-001, REQ-QOS-001, REQ-REPRO-001, REQ-OBS-001 |
| `EXT-SUST-WRITE-300S` | REQ-SUST-001, REQ-SUST-002, REQ-QOS-001, REQ-REPRO-001, REQ-OBS-001 |
| `EXT-SUST-READ-120S` | REQ-SUST-003, REQ-QOS-001, REQ-REPRO-001, REQ-OBS-001 |
| `EXT-STATE-IDLE-START-PROBE` | REQ-STATE-001, REQ-QOS-001, REQ-REPRO-001, REQ-OBS-001 |
| `EXT-STATE-WRITE-CONDITION` | REQ-STATE-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-STATE-POST-WRITE-PROBE` | REQ-STATE-001, REQ-QOS-001, REQ-REPRO-001, REQ-OBS-001 |
| `EXT-STATE-REPRO-BASELINE` | REQ-STATE-REPRO-002, REQ-QOS-001, REQ-OBS-001 |
| `EXT-STATE-REPRO-CONDITION` | REQ-STATE-REPRO-002, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-STATE-REPRO-POST` | REQ-STATE-REPRO-002, REQ-QOS-001, REQ-OBS-001 |

## Verdict Vocabulary

Use conservative verdict wording:

- `Pass`: required evidence exists and meets the defined rule.
- `Observation`: evidence exists, but no mature threshold has been defined yet.
- `Limited`: the test ran, but environment, permissions, or tooling limited interpretation.
- `Blocked`: the test could not run or critical evidence is missing.

Avoid claiming internal SSD root cause unless device-level or firmware-level evidence exists.
