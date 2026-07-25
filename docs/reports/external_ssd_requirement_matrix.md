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
| REQ-LARGE-WS-001 | Sequential write and read behavior shall be captured over a 32 GiB completion-based file target with time-window evidence. | experiment manifest, fio JSON, time-series and window CSVs | Pass if write/read complete the planned bytes and preserve first/middle/last evidence |
| REQ-MIXED-001 | Concurrent 4K random read/write behavior shall be measured with read and write throughput and tail latency reported separately. | experiment manifest, fio JSON, per-direction summary and repeatability CSVs | Pass if three 70:30 mixed runs contain nonzero read/write I/O and separate p99/p99.9 evidence |
| REQ-MIXED-CTRL-002 | The 70:30 mixed result shall be compared with matched 100% random-read and 100% random-write controls. | control experiment manifest, fio JSON, comparison CSV | Pass if both pure controls complete three matching repeats and preserve per-direction QoS evidence |
| REQ-MIXED-ABBA-003 | Read QoS under pure-read and 70:30 mixed load shall be compared in an A-B-B-A sequence that exposes first/last order and carry-over effects. | ABBA experiment manifest, four fio JSON files, phase comparison CSV | Pass if A1/B1/B2/A2 complete with matching controls and per-phase read p99/p99.9 evidence |
| REQ-MIXED-BAAB-004 | The ABBA read-QoS observation shall be challenged in an independent reconnect-start B-A-A-B session with reversed workload order. | BAAB experiment manifest, four fio JSON files, joint phase comparison | Pass if B1/A1/A2/B2 complete with reconnect and same-port confirmations and per-phase read p99/p99.9 evidence |
| REQ-MIXED-RATIO-005 | Mixed 90:10, 70:30, and 50:50 response shall be mapped with each ratio represented once in every sequence position. | sweep manifest, nine fio JSON files, ratio-by-cycle-by-position comparison | Pass if all nine phases complete, preserve their requested mixes, and retain cycle and position in the analysis |
| REQ-MIXED-RATIO-REPRO-006 | The counterbalanced ratio response and phase-transition pattern shall be challenged in an independently initiated session with a different ratio order. | Session 2 manifest, nine fio JSON files, cross-session comparison | Pass if Session 2 preserves all controls, places each ratio once per cycle and position, and reports cross-session direction agreement |
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
| `EXT-LARGE-WS-SEQ-WRITE-32G` | REQ-LARGE-WS-001, REQ-QOS-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-LARGE-WS-SEQ-READ-32G` | REQ-LARGE-WS-001, REQ-QOS-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-RW-7030-4K-QD16` | REQ-MIXED-001, REQ-QOS-001, REQ-REPRO-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-CONTROL-RANDREAD-4K-QD16` | REQ-MIXED-CTRL-002, REQ-QOS-001, REQ-REPRO-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-CONTROL-RANDWRITE-4K-QD16` | REQ-MIXED-CTRL-002, REQ-QOS-001, REQ-REPRO-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-ABBA-PURE-READ` | REQ-MIXED-ABBA-003, REQ-QOS-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-ABBA-7030` | REQ-MIXED-ABBA-003, REQ-QOS-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-BAAB-PURE-READ` | REQ-MIXED-BAAB-004, REQ-QOS-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-BAAB-7030` | REQ-MIXED-BAAB-004, REQ-QOS-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-RATIO-SWEEP-001` | REQ-MIXED-RATIO-005, REQ-QOS-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |
| `EXT-MIXED-RATIO-SWEEP-REPRO-002` | REQ-MIXED-RATIO-REPRO-006, REQ-QOS-001, REQ-ENV-001, REQ-OBS-001, REQ-TRACE-001 |

## Verdict Vocabulary

Use conservative verdict wording:

- `Pass`: required evidence exists and meets the defined rule.
- `Observation`: evidence exists, but no mature threshold has been defined yet.
- `Limited`: the test ran, but environment, permissions, or tooling limited interpretation.
- `Blocked`: the test could not run or critical evidence is missing.

Avoid claiming internal SSD root cause unless device-level or firmware-level evidence exists.
