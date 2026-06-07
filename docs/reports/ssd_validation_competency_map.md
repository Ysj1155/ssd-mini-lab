# SSD Validation Competency Map

## Purpose

This document maps the SSD mini-lab work to validation-engineering competencies.

The project is not only a fio benchmark collection. It is a practice track for explaining how test conditions, measurement quality, reproducibility, and limitations affect storage validation.

## Competency Summary

| Competency | Evidence in this repo | What it demonstrates |
|---|---|---|
| Test condition definition | Baseline, QD sweep, direct/buffered, WSL path compare, sustained smoke | Ability to define workload, block size, queue depth, direct mode, path, runtime, and repeat count |
| Result parsing | `parse_fio_results.py` | Ability to turn raw fio JSON into structured, comparable metrics |
| Metric selection | p95, p99, p99.9, CV, first-vs-last ratios | Understanding that average throughput alone is not enough |
| Reproducibility review | `reproducibility_qd_sweep.md` | Ability to evaluate run-to-run variation instead of trusting one run |
| Cache/path awareness | `direct_buffered_week7.md`, `wsl_path_compare_week9.md` | Ability to distinguish device behavior from OS/filesystem/path effects |
| Environment control | `environment_collection_week8.md` | Ability to capture test environment before interpreting data |
| Sustained workload thinking | `sustained_workload_week10.md` | Ability to inspect stability over time and identify latency-spike candidates |
| Limitation handling | README and report interpretation sections | Ability to avoid over-claiming SSD-internal causes from file-based tests |

## Experiment-To-Skill Mapping

### Baseline fio Analysis

Evidence:

- `parse_fio_results.py`
- `plot_fio_summary.py`
- `docs/reports/baseline_v1.md`

Skill signal:

- Establishes a controlled starting point.
- Separates sequential and random workloads.
- Converts raw benchmark output into CSV and plots.

Interview framing:

> I started with baseline fio workloads to build a repeatable measurement pipeline before adding more complex variables.

### Queue-Depth Sweep

Evidence:

- `analyze_qd_sweep.py`
- `docs/reports/reproducibility_qd_sweep.md`

Skill signal:

- Shows how queue depth affects throughput and tail latency.
- Identifies that higher QD can improve IOPS while increasing p99 latency.
- Uses CV to review stability.

Interview framing:

> I used QD sweep results to compare performance scaling against latency cost, then reviewed run-to-run variation with CV.

### Direct I/O vs Buffered I/O

Evidence:

- `analyze_direct_buffered.py`
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
- `analyze_wsl_path_compare.py`
- `docs/reports/wsl_path_compare_week9.md`

Skill signal:

- Captures Windows and WSL environment context.
- Compares WSL native ext4 and `/mnt/d` as different paths.
- Labels path-level effects instead of treating all fio runs as equivalent SSD tests.

Interview framing:

> I learned that the path itself is part of the test condition. WSL ext4 and `/mnt/d` can produce very different results, so path labeling is mandatory.

### QoS and Tail Latency Review

Evidence:

- `analyze_qos_tail_latency.py`
- `docs/reports/qos_tail_latency_review.md`

Skill signal:

- Collects p99, p99.9, and CV across earlier experiments.
- Moves the analysis from "fastest condition" to "stable and predictable condition."
- Builds validation language around QoS instead of headline throughput.

Interview framing:

> I used p99, p99.9, and variation to evaluate stability. Average IOPS alone is not enough for validation.

### Sustained Workload Smoke

Evidence:

- `run_sustained_smoke.ps1`
- `analyze_sustained_smoke.py`
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
- results include filesystem and OS effects
- external-drive results can include USB/enclosure behavior
- SMART/NVMe telemetry is not collected yet
- sustained testing has only one smoke run so far

This is not a weakness if stated clearly. For a validation engineer, knowing what a test cannot prove is part of the skill.

## Strongest Portfolio Story

The strongest story from this repo is:

1. I built a repeatable fio result pipeline.
2. I expanded the test matrix one variable at a time.
3. I compared performance, tail latency, and variation.
4. I documented path/cache/environment limitations.
5. I moved from short benchmark runs toward sustained stability analysis.

## Next Skill Targets

The next useful skill targets are:

1. Repeat the sustained smoke run three times and compare variation.
2. Add a longer sustained profile after the smoke test is stable.
3. Add environment snapshots beside each major run.
4. Add telemetry if a safe, non-destructive path becomes available.
5. Turn the project into a concise Korean portfolio README after the technical story is stable.
