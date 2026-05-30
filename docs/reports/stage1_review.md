p# Stage 1 Review - fio-based SSD Validation Mini Lab

## Purpose

Stage 1 built a small but repeatable fio-based SSD validation flow.

The focus was not absolute device performance. The focus was learning how to define test conditions, collect structured results, parse them consistently, visualize key metrics, and explain the limits of each result.

## Scope

Stage 1 covers the first Windows file-based validation loop:

| Area | Status | Main artifact |
|---|---|---|
| Baseline workload runs | Done | `docs/reports/baseline_v1.md` |
| fio JSON parser | Done | `parse_fio_results.py` |
| Baseline plots | Done | `plot_fio_summary.py`, `results/plots/` |
| Queue-depth sweep | Done | `analyze_qd_sweep.py`, `results/qd_sweep_grouped.csv` |
| QD reproducibility | Done | `analyze_qd_reproducibility.py`, `results/qd_sweep_reproducibility.csv` |
| Direct vs buffered I/O | Done | `analyze_direct_buffered.py`, `docs/reports/direct_buffered_week7.md` |

## Repository Outputs

| Output | Role |
|---|---|
| `results/fio_summary.csv` | Baseline per-run summary |
| `results/plots/` | Baseline workload plots |
| `results/qd_sweep_summary.csv` | QD sweep per-run summary |
| `results/qd_sweep_grouped.csv` | QD sweep grouped summary |
| `results/qd_sweep_reproducibility.csv` | QD sweep run-to-run stability summary |
| `results/qd_sweep_plots/` | QD sweep and reproducibility plots |
| `results/direct_buffered_summary.csv` | Direct/buffered per-run summary |
| `results/direct_buffered_grouped.csv` | Direct/buffered grouped summary |
| `results/direct_buffered_comparison.csv` | Buffered-over-direct ratios |
| `results/direct_buffered_plots/` | Direct/buffered comparison plots |

## Baseline Findings

The baseline measured sequential and random read/write workloads with three repeated runs.

| workload | Avg BW (MiB/s) | Avg IOPS | Avg p99 clat (us) | p99 CV |
|---|---:|---:|---:|---:|
| seq_read | 524.43 | 523.76 | 92,449.45 | 0.1902 |
| seq_write | 480.35 | 479.32 | 118,314.33 | 0.0819 |
| rand_read | 214.42 | 54,891.75 | 722.26 | 0.0285 |
| rand_write | 126.41 | 32,360.71 | 1,182.38 | 0.0080 |

Observations:

- Sequential read/write bandwidth was stable across repeated runs.
- Random write showed lower IOPS and higher p99 latency than random read.
- Sequential p99 latency had higher run-to-run variation than average bandwidth.
- Mean performance alone was not enough to describe workload behavior.

## QD Sweep Findings

The QD sweep compared random 4K read/write behavior across QD 1, 4, 16, and 32.

| workload | QD | Avg BW (MiB/s) | Avg IOPS | Avg p99 clat (us) |
|---|---:|---:|---:|---:|
| rand_read | 1 | 20.41 | 5,225.49 | 286.04 |
| rand_read | 4 | 80.79 | 20,681.08 | 314.71 |
| rand_read | 16 | 203.94 | 52,207.00 | 505.86 |
| rand_read | 32 | 209.96 | 53,749.12 | 804.18 |
| rand_write | 1 | 46.06 | 11,790.25 | 108.37 |
| rand_write | 4 | 124.41 | 31,849.25 | 158.72 |
| rand_write | 16 | 126.64 | 32,418.56 | 607.57 |
| rand_write | 32 | 122.55 | 31,371.02 | 1,280.68 |

Observations:

- `rand_read` scaled strongly from QD1 to QD16, then showed only small gain at QD32.
- `rand_write` mostly saturated around QD4 to QD16.
- Higher QD improved parallelism, but p99 latency increased sharply.
- `rand_write QD32` was a poor QoS tradeoff: it did not improve throughput, but p99 latency increased heavily.

## Reproducibility Findings

Run-to-run stability was evaluated with CV:

```text
CV = standard deviation / mean
```

| Metric | Highest-variation condition | CV |
|---|---|---:|
| bandwidth | rand_read QD16 | 0.0639 |
| IOPS | rand_read QD16 | 0.0639 |
| p99 latency | rand_write QD32 | 0.0943 |

Observations:

- Most throughput and IOPS CV values were low enough for a first-pass mini-lab.
- Tail latency varied more than average throughput in several cases.
- Repeated runs made it possible to separate a single lucky/unlucky run from a repeatable pattern.

## Direct vs Buffered Findings

Week 7 compared `direct=1` and `direct=0` with random 4K read/write at QD16.

| workload | mode | Avg BW (MiB/s) | Avg IOPS | Avg p99 clat (us) |
|---|---|---:|---:|---:|
| rand_read | direct=1 | 213.92 | 54,762.40 | 392.53 |
| rand_read | direct=0 | 351.89 | 90,083.22 | 343.38 |
| rand_write | direct=1 | 125.72 | 32,184.05 | 667.65 |
| rand_write | direct=0 | 178.26 | 45,635.12 | 467.63 |

Buffered-over-direct ratios:

| workload | BW ratio | IOPS ratio | p99 latency ratio |
|---|---:|---:|---:|
| rand_read | 1.645 | 1.645 | 0.875 |
| rand_write | 1.418 | 1.418 | 0.700 |

Observations:

- Buffered I/O reported higher bandwidth and IOPS.
- Buffered I/O also reported lower p99 latency in this run.
- This should be interpreted as OS/filesystem-cache influence, not as proof that the SSD media path is faster.
- `direct=1` remains the more appropriate setting when the goal is to reduce page-cache influence.

## Parser and Automation Improvements

The parser evolved from a baseline-only parser into a more general fio result parser.

Important improvements:

- Handles fio output that has warning text before the JSON object.
- Extracts run number from filenames.
- Extracts QD metadata such as `qd16`.
- Extracts direct/buffered metadata such as `direct0` and `direct1`.
- Keeps fio runtime option values such as `iodepth` and `direct`.
- Preserves both filename metadata and fio job options so mismatches can be detected.

This matters because validation results are only useful when the conditions are recoverable from the output files.

## Validation Lessons

Stage 1 produced several practical validation lessons:

1. Test metadata is part of the result.
2. Higher IOPS is not automatically a better condition.
3. p99 latency can reveal behavior hidden by average throughput.
4. Repeated runs are necessary before trusting a pattern.
5. Buffered I/O can make results look better while making interpretation harder.
6. A result should include both interpretation and limitations.
7. A parser bug can become an analysis bug if filename metadata is not handled carefully.

## Current Limitations

| Limitation | Impact |
|---|---|
| Windows file-based fio tests | Results include OS and filesystem path effects |
| External SSD over USB/enclosure | Device behavior cannot be fully separated from interface effects |
| Three repeats per condition | Good for first-pass stability, not enough for strong statistical claims |
| 30 second runtime | Does not cover long sustained workload behavior |
| No SMART/NVMe telemetry | Cannot confirm temperature, throttling, media errors, or internal device state |
| No raw block-device test | Safer for a personal laptop, but less representative of low-level device validation |

These limitations are acceptable for Stage 1 because the objective was to build the validation workflow safely.

## Portfolio Value

Stage 1 can be presented as a practical validation mini-lab:

- Built a repeatable fio result pipeline.
- Compared baseline workloads and QD behavior.
- Added reproducibility analysis with CV.
- Investigated direct I/O vs buffered I/O.
- Documented why OS cache effects matter.
- Preserved raw JSON, parsed CSV, plots, and reports.

Interview-ready summary:

> I built a fio-based SSD mini-lab to practice validation thinking. I measured baseline workloads, swept queue depth, checked run-to-run reproducibility, and compared direct I/O with buffered I/O. The key lesson was that average throughput alone is not enough: p99 latency, repeated-run stability, and test-path effects such as OS cache must be considered before interpreting a result.

## Recommended Next Stage

Stage 2 should move from short benchmark summaries toward system-level validation thinking.

Recommended next tasks:

1. Add environment collection scripts for Windows and WSL/Linux.
2. Compare Windows file path and WSL path behavior where safe.
3. Add longer sustained workload runs.
4. Create a QoS-focused report centered on p95/p99/p99.9 latency.
5. Write Obsidian TIL notes that explain the lessons in Korean for interview preparation.

## Stage 1 Completion Assessment

| Area | Assessment |
|---|---|
| Result collection | Solid for first stage |
| Parser/automation | Solid and extensible |
| Visualization | Good enough for portfolio review |
| Reproducibility | Present, but needs more repeats for stronger claims |
| Hardware observability | Weak; telemetry is missing |
| Documentation | Good, with room for a Korean interview-oriented version |

Overall Stage 1 status: complete enough to pause, review, and move into Stage 2.
