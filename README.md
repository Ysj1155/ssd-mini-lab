# SSD Mini Lab

Black-box SSD validation mini-lab using fio, Python, and PowerShell.

This repository treats a real SSD as a DUT (Device Under Test) and preserves a traceable validation flow:

```text
requirement -> condition -> runner / observer -> raw evidence -> analysis -> verdict
```

The goal is not to chase the highest benchmark number. The goal is to show controlled execution, reproducible evidence, tail-latency review, and honest interpretation limits.

This project is intentionally separate from the FTL/GC white-box study project. This repository measures externally observable device behavior; it does not claim internal NAND, FTL, or GC root cause.

## Current Track: External SSD DUT

The active track uses a SanDisk external SSD and a file target at `E:\validation\ssd_lab_fio_testfile`.

Interpretation boundary: results include the USB path, Windows, exFAT, and fio file-target effects.

| Validation question | Current evidence |
|---|---|
| How does QD affect 4K random performance and tail latency? | QD 1/4/16/32, read/write, 30s, repeat=3 |
| Are results repeatable? | Per-condition mean, standard deviation, and CV |
| Does sustained behavior differ from the short sweep? | Read/write QD16/QD32, 120s, repeat=3 |
| Does longer runtime expose write-side QoS risk? | Random write QD32, 120s vs 300s, repeat=3 |
| Can every result be traced to its conditions and evidence? | Run manifest plus separate runner/observer manifests |
| How does random-I/O response scale with block size? | Completed 4K/64K/1M, QD32, repeat=3 read/write sessions; 64K was the observed throughput knee |
| Can a newly written file be read back without data-path corruption? | Completed 4 GiB CRC32C write/readback: integrity Pass |
| Can transient fio behavior be correlated with host-visible storage activity? | First synchronized run produced only zero-valued counters: Limited |

Latest finding: two independent counterbalanced mixed-ratio sessions disagreed on bandwidth and read-p99 ratio rank, cycle rank, position rank, and Phase 5 direction. The automated verdict is `not_reproduced_across_independent_counterbalanced_sessions`.

The completed `EXT-IDLE-RAMP-001` protocol isolated requested pre-probe idle at 0/60/300 seconds under one fixed 70:30 workload. All mirrored pairs agreed that the prior 37-53 second ramp was absent, while average bandwidth remained unstable across the 0-second and 300-second pairs. The verdict is `no_clear_idle_duration_association`.

The completed controlled block-size protocol closed the remaining baseline roadmap item with independent random-read and random-write sessions. At QD32, 64K reached the observed throughput plateau while 1M added no bandwidth and increased p99 latency by more than 13x versus 64K. The next project phase moves from broader performance sweeps to file-target integrity, synchronized observation, and requirement-based regression.

`EXT-DATA-INTEGRITY-001` is now complete. A new 4 GiB target was written and fully read back with CRC32C under fio 3.42: both phases processed exactly 4,294,967,296 bytes with job error 0, so integrity passed. The synchronized Windows logical-disk observer produced timestamped samples but no nonzero workload signal, so host-observer evidence is explicitly Limited rather than treated as complete.

The earlier three-session conditioning study and both mixed-ratio sessions preserve reconnect and same-port confirmations, complete manifests, matching observer/runner evidence, and automated comparison CSVs. Requirements pass when their evidence plans complete even when the performance direction does not reproduce.

`EXT-LARGE-WS-SEQ-001` completed one 32 GiB sequential overwrite/read observation without a late-run throughput drop. The completed A-B-B-A and reconnect-start B-A-A-B sessions produced opposite directions, so repeatable 70:30 read-tail inflation was `not reproduced`. Two independent counterbalanced 90:10 / 70:30 / 50:50 sessions then disagreed on ratio, cycle, position, and Phase 5 directions. The analyzer records transition time and the cross-session verdict as `not_reproduced_across_independent_counterbalanced_sessions`. None of these experiments is evidence of internal cache, FTL, or GC behavior.

## Start Here

| Purpose | Path |
|---|---|
| DUT definition | `docs/reports/external_ssd_dut_profile.md` |
| Requirements and verdict rules | `docs/reports/external_ssd_requirement_matrix.md` |
| Next execution procedure | `docs/reports/external_ssd_execution_runbook.md` |
| Current result interpretation | `docs/reports/external_ssd_product_validation.md` |
| Next-stage roadmap | `docs/reports/external_ssd_project_roadmap.md` |
| File-integrity execution | `docs/reports/external_ssd_data_integrity_runbook.md` |
| File-integrity result | `docs/reports/external_ssd_data_integrity_result.md` |
| Synchronized host observer | `docs/reports/windows_host_counter_observer.md` |
| Machine-readable test matrix | `configs/external_ssd_validation_matrix.yaml` |
| Raw fio JSON and logs | `results/external_ssd/` |
| Parsed sustained CSVs | `results/external_ssd_sustained_*.csv` |

## Evidence Model

- Runner: executes fio and writes raw JSON/logs plus `runner_manifest.json`.
- Observer: collects read-only environment and telemetry evidence before and after fio.
- Analyzer: converts fio JSON/logs into comparable CSV summaries.
- Integrated manifest: links the DUT, requirements, conditions, artifacts, and evidence gaps under one `run_id`.
- Report: records observations, verdicts, anomalies, and interpretation boundaries.

Missing telemetry or execution evidence is recorded as `limited`; it is not silently treated as complete.

## Repository Layout

```text
ssd-mini-lab/
  configs/                 # machine-readable validation conditions
  docs/reports/            # runbook, requirements, and result reports
  fio/                     # small baseline fio samples
  results/                 # raw evidence and derived CSVs
  scripts/analysis/        # parsers, analyzers, manifest builder
  scripts/observers/       # read-only environment/telemetry collection
  scripts/runners/         # fio execution
  tests/                   # parser compatibility fixtures and tests
```

Large local fio test files are ignored by Git. Raw JSON/logs and derived CSVs are retained when they support a documented validation result.

## Verification

```powershell
cd D:\ssd_lab
python -m unittest discover -s tests -p "test_*.py"
python .\scripts\analysis\analyze_external_ssd_sustained.py
python .\scripts\analysis\analyze_external_ssd_mixed_ratio_sweep.py
python .\scripts\analysis\build_external_ssd_run_manifest.py --all
```

Codex does not run fio for the external SSD track unless explicitly asked. The user confirms the target path and runs fio locally.
