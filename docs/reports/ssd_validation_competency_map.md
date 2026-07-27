# SSD Validation Competency Map

## Purpose

This document maps the SSD mini-lab work to validation-engineering competencies.

The project is not only a fio benchmark collection. It is a practice track for explaining how test conditions, measurement quality, reproducibility, and limitations affect storage validation.

## Competency Summary

| Competency | Evidence in this repo | What it demonstrates |
|---|---|---|
| Test condition definition | Baseline, QD sweep, direct/buffered, WSL path compare, sustained smoke | Ability to define workload, block size, queue depth, direct mode, path, runtime, and repeat count |
| Result parsing | `scripts/analysis/parse_fio_results.py` | Ability to turn raw fio JSON into structured, comparable metrics |
| Metric selection | p95, p99, p99.9, CV, first-vs-last ratios | Understanding that average throughput alone is not enough |
| Reproducibility review | `reproducibility_qd_sweep.md` | Ability to evaluate run-to-run variation instead of trusting one run |
| Cache/path awareness | `direct_buffered_week7.md`, `wsl_path_compare_week9.md` | Ability to distinguish device behavior from OS/filesystem/path effects |
| Environment control | `environment_collection_week8.md` | Ability to capture test environment before interpreting data |
| Sustained workload thinking | `sustained_workload_week10.md` | Ability to inspect stability over time and identify latency-spike candidates |
| Limitation handling | README and report interpretation sections | Ability to avoid over-claiming SSD-internal causes from file-based tests |

## Experiment-To-Skill Mapping

### Baseline fio Analysis

Evidence:

- `scripts/analysis/parse_fio_results.py`
- `scripts/analysis/plot_fio_summary.py`
- `docs/reports/baseline_v1.md`

Skill signal:

- Establishes a controlled starting point.
- Separates sequential and random workloads.
- Converts raw benchmark output into CSV and plots.

Interview framing:

> I started with baseline fio workloads to build a repeatable measurement pipeline before adding more complex variables.

### Queue-Depth Sweep

Evidence:

- `scripts/analysis/analyze_qd_sweep.py`
- `docs/reports/reproducibility_qd_sweep.md`

Skill signal:

- Shows how queue depth affects throughput and tail latency.
- Identifies that higher QD can improve IOPS while increasing p99 latency.
- Uses CV to review stability.

Interview framing:

> I used QD sweep results to compare performance scaling against latency cost, then reviewed run-to-run variation with CV.

### Direct I/O vs Buffered I/O

Evidence:

- `scripts/analysis/analyze_direct_buffered.py`
- `docs/reports/direct_buffered_week7.md`

Skill signal:

- Separates fio's direct mode from filename metadata.
- Shows that buffered I/O can make results look better because of OS/filesystem cache behavior.
- Avoids claiming that buffered results prove the SSD media path is faster.

Interview framing:

> I treated direct and buffered I/O as different test paths, not just different performance numbers.

### Environment and WSL Path Comparison

Evidence:

- `scripts/collect_env_windows.ps1`
- `docs/reports/environment_collection_week8.md`
- `scripts/analysis/analyze_wsl_path_compare.py`
- `docs/reports/wsl_path_compare_week9.md`

Skill signal:

- Captures Windows and WSL environment context.
- Compares WSL native ext4 and `/mnt/d` as different paths.
- Labels path-level effects instead of treating all fio runs as equivalent SSD tests.

Interview framing:

> I learned that the path itself is part of the test condition. WSL ext4 and `/mnt/d` can produce very different results, so path labeling is mandatory.

### QoS and Tail Latency Review

Evidence:

- `scripts/analysis/analyze_qos_tail_latency.py`
- `docs/reports/qos_tail_latency_review.md`

Skill signal:

- Collects p99, p99.9, and CV across earlier experiments.
- Moves the analysis from "fastest condition" to "stable and predictable condition."
- Builds validation language around QoS instead of headline throughput.

Interview framing:

> I used p99, p99.9, and variation to evaluate stability. Average IOPS alone is not enough for validation.

### Sustained Workload Smoke

Evidence:

- `scripts/runners/run_sustained_smoke.ps1`
- `scripts/analysis/analyze_sustained_smoke.py`
- `docs/reports/sustained_workload_week10.md`

Skill signal:

- Extends short tests into a time-based sustained workload.
- Compares first third vs last third behavior.
- Tracks max latency and average-latency spike candidates separately.

Interview framing:

> I started with a conservative sustained smoke run, then separated aggregate max latency from time-window average latency so that I would not over-interpret one outlier.

## What This Project Does Not Prove Yet

This lab currently does not prove internal NAND, controller, FTL, SLC cache, thermal-throttling, or garbage-collection behavior directly.

Reasons:

- tests are file-based
- results include filesystem, Windows, and USB/enclosure effects
- SMART and reliability telemetry remain limited through the current access path
- no direct power measurement or firmware/NAND trace is available
- no external product specification defines hard performance thresholds

This is not a weakness if stated clearly. For a validation engineer, knowing what a test cannot prove is part of the skill.

## Strongest Portfolio Story

The strongest story from this repo is:

1. I built a repeatable fio result and evidence pipeline.
2. I expanded the matrix one controlled variable at a time.
3. I separated throughput, tail latency, repeatability, and order effects.
4. I challenged attractive hypotheses with independent counterbalanced sessions.
5. I preserved negative results and explicit interpretation boundaries.
6. I linked requirements, runners, observers, raw data, analyzers, and verdicts through manifests.

## Next Skill Targets

Completed foundations:

- repeated and longer sustained profiles
- environment snapshots and permission-aware telemetry
- counterbalanced mixed, idle, and block-size studies
- automated parser/analyzer regression tests

Next targets:

1. Define a compact requirement-based regression profile using stable performance and integrity conditions.
2. Keep synchronized Windows logical-disk evidence Limited unless a provider produces nonzero workload samples.
3. Create audience-specific portfolio or interview material only when requested.

See `external_ssd_project_roadmap.md`.
