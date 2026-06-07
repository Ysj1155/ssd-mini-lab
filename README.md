# SSD Mini Lab

fio-based SSD validation mini-lab for learning, portfolio building, and interview preparation.

The goal is not to chase the highest benchmark number. The goal is to build a repeatable validation flow:

- define test conditions
- collect fio JSON results
- parse results into CSV
- visualize bandwidth, IOPS, and latency
- compare repeated runs
- document interpretation and limitations

For portfolio review, the project is mapped to SSD validation competencies in:

```text
docs/reports/ssd_validation_competency_map.md
```

Korean interview talking points are summarized in:

```text
docs/reports/korean_interview_brief.md
```

Reusable validation run checklist:

```text
docs/reports/validation_run_checklist.md
```

Stage 2 next experiment plan:

```text
docs/reports/stage2_next_experiment_plan.md
```

## Current Status

| Area | Status | Main outputs |
|---|---|---|
| SSD validation competency map | Done | `docs/reports/ssd_validation_competency_map.md` |
| Korean interview brief | Done | `docs/reports/korean_interview_brief.md` |
| Validation run checklist | Done | `docs/reports/validation_run_checklist.md` |
| Stage 2 next experiment plan | Ready | `docs/reports/stage2_next_experiment_plan.md` |
| Baseline fio parsing | Done | `parse_fio_results.py`, `results/fio_summary.csv` |
| Baseline plots | Done | `plot_fio_summary.py`, `results/plots/` |
| Queue-depth sweep | Done | `analyze_qd_sweep.py`, `results/qd_sweep_grouped.csv`, `results/qd_sweep_plots/` |
| QD reproducibility | Done | `analyze_qd_reproducibility.py`, `results/qd_sweep_reproducibility.csv` |
| Week 7 direct vs buffered | Done | `analyze_direct_buffered.py`, `results/direct_buffered_*`, `results/direct_buffered_plots/` |
| Stage 1 review | Done | `docs/reports/stage1_review.md` |
| Week 8 environment collection | Done | `scripts/collect_env_windows.ps1`, `docs/reports/environment_collection_week8.md` |
| Week 9 WSL path comparison | Done | `run_wsl_path_compare.ps1`, `analyze_wsl_path_compare.py`, `results/wsl_path_compare_*` |
| QoS/tail latency review | Done | `analyze_qos_tail_latency.py`, `docs/reports/qos_tail_latency_review.md` |
| Week 10 sustained smoke | Done (repeat smoke) | `run_sustained_smoke.ps1`, `analyze_sustained_smoke.py`, `docs/reports/sustained_workload_week10.md` |

## Repository Layout

```text
ssd-mini-lab/
  parse_fio_results.py
  plot_fio_summary.py
  analyze_qd_sweep.py
  analyze_qd_reproducibility.py
  analyze_direct_buffered.py
  run_baseline.ps1
  run_qd_sweep.ps1
  run_direct_buffered.ps1
  docs/
    notes/
    reports/
  fio/
  results/
    plots/
    qd_sweep/
    qd_sweep_plots/
    direct_buffered/
    direct_buffered_plots/
```

Large temporary fio test files are ignored by Git. Result JSON/CSV/plot files are kept when they are part of a documented experiment.

## Tools

- fio
- Python
- pandas
- matplotlib
- PowerShell on Windows
- Git / GitHub

## 1. Parse fio JSON

`parse_fio_results.py` reads fio JSON output and creates validation-oriented CSV summaries.

Extracted fields include:

- workload
- run number
- QD from filename
- direct flag from filename
- fio runtime options such as `rw`, `bs`, `iodepth`, `direct`
- bandwidth in MiB/s
- IOPS
- mean completion latency
- p95 / p99 / p99.9 completion latency

Baseline parse:

```powershell
cd D:\ssd_lab
python .\parse_fio_results.py
```

QD sweep parse:

```powershell
cd D:\ssd_lab
python .\parse_fio_results.py `
  --input-dir D:\ssd_lab\results\qd_sweep `
  --output D:\ssd_lab\results\qd_sweep_summary.csv
```

Direct/buffered parse:

```powershell
cd D:\ssd_lab
python .\parse_fio_results.py `
  --input-dir D:\ssd_lab\results\direct_buffered `
  --output D:\ssd_lab\results\direct_buffered_summary.csv
```

## 2. Baseline Analysis

Baseline results cover four workloads:

- `seq_read`
- `seq_write`
- `rand_read`
- `rand_write`

Generate baseline plots:

```powershell
cd D:\ssd_lab
python .\plot_fio_summary.py
```

Outputs:

```text
results/fio_summary.csv
results/plots/
docs/reports/baseline_v1.md
```

## 3. Queue-Depth Sweep

QD sweep compares random 4K read/write behavior across QD 1, 4, 16, and 32.

Generate grouped summaries and plots:

```powershell
cd D:\ssd_lab
python .\analyze_qd_sweep.py
```

Outputs:

```text
results/qd_sweep_summary.csv
results/qd_sweep_grouped.csv
results/qd_sweep_plots/
docs/notes/parameter_sweep.md
```

Key QD sweep result:

| workload | QD | Avg Bandwidth (MiB/s) | Avg IOPS | Avg p99 latency (us) |
|---|---:|---:|---:|---:|
| rand_read | 1 | 20.41 | 5,225.49 | 286.04 |
| rand_read | 4 | 80.79 | 20,681.08 | 314.71 |
| rand_read | 16 | 203.94 | 52,207.00 | 505.86 |
| rand_read | 32 | 209.96 | 53,749.12 | 804.18 |
| rand_write | 1 | 46.06 | 11,790.25 | 108.37 |
| rand_write | 4 | 124.41 | 31,849.25 | 158.72 |
| rand_write | 16 | 126.64 | 32,418.56 | 607.57 |
| rand_write | 32 | 122.55 | 31,371.02 | 1,280.68 |

Interpretation:

- `rand_read` improves up to QD16, then shows smaller gain at QD32.
- `rand_write` mostly saturates around QD4 to QD16.
- p99 latency increases as QD rises.
- Highest IOPS is not always the best validation condition when QoS and tail latency matter.

## 4. QD Reproducibility

`analyze_qd_reproducibility.py` evaluates run-to-run variation across repeated QD sweep runs.

```powershell
cd D:\ssd_lab
python .\analyze_qd_reproducibility.py
```

Outputs:

```text
results/qd_sweep_reproducibility.csv
results/qd_sweep_plots/qd_sweep_iops_cv.png
results/qd_sweep_plots/qd_sweep_bandwidth_cv.png
results/qd_sweep_plots/qd_sweep_p99_cv.png
results/qd_sweep_plots/qd_sweep_p99_run_to_run.png
docs/reports/reproducibility_qd_sweep.md
```

CV is used as the stability metric:

```text
CV = standard deviation / mean
```

Notable reproducibility results:

| Metric | Highest-variation condition | CV |
|---|---|---:|
| bandwidth | rand_read QD16 | 0.0639 |
| IOPS | rand_read QD16 | 0.0639 |
| p99 latency | rand_write QD32 | 0.0943 |

## 5. Week 7 Direct I/O vs Buffered I/O

Week 7 compares random 4K read/write with `direct=1` and `direct=0`.

Run the experiment:

```powershell
cd D:\ssd_lab
.\run_direct_buffered.ps1
```

Rebuild parser output and analysis:

```powershell
cd D:\ssd_lab

python .\parse_fio_results.py `
  --input-dir D:\ssd_lab\results\direct_buffered `
  --output D:\ssd_lab\results\direct_buffered_summary.csv

python .\analyze_direct_buffered.py
```

Outputs:

```text
results/direct_buffered_summary.csv
results/direct_buffered_grouped.csv
results/direct_buffered_comparison.csv
results/direct_buffered_plots/
docs/reports/direct_buffered_week7.md
```

The parser now handles filenames such as `rand_read_direct0_run1.json` correctly:

- `workload` is normalized to `rand_read` or `rand_write`
- `direct_from_filename` stores `0` or `1`
- fio's actual `direct` job option is preserved in the `direct` column

Latest grouped result:

| Workload | Mode | Avg BW (MiB/s) | Avg IOPS | Avg p99 clat (us) |
|---|---|---:|---:|---:|
| rand_read | direct=1 | 213.92 | 54,762.40 | 392.53 |
| rand_read | direct=0 | 351.89 | 90,083.22 | 343.38 |
| rand_write | direct=1 | 125.72 | 32,184.05 | 667.65 |
| rand_write | direct=0 | 178.26 | 45,635.12 | 467.63 |

Buffered-over-direct ratios:

| Workload | BW ratio | IOPS ratio | p99 latency ratio |
|---|---:|---:|---:|
| rand_read | 1.645 | 1.645 | 0.875 |
| rand_write | 1.418 | 1.418 | 0.700 |

The buffered path reports higher throughput and lower p99 latency in this Windows file-based setup. This should be interpreted as OS/filesystem-cache influence, not as proof that the SSD media path is faster.

## Validation Notes

This mini-lab is meant to practice validation thinking:

1. Test conditions must be explicit.
2. Result parsing must preserve metadata such as workload, run number, QD, and direct mode.
3. Average throughput alone is not enough; p95/p99 latency and run-to-run variation matter.
4. Buffered I/O can make results look better, but cache effects must be called out.
5. Current results cannot directly prove internal SSD causes such as GC, SLC cache behavior, FTL behavior, or thermal throttling.

The portfolio-oriented competency map is kept in:

```text
docs/reports/ssd_validation_competency_map.md
```

It connects each experiment to practical validation skills such as test-condition definition, result parsing, QoS review, reproducibility review, path/cache awareness, environment control, and sustained-workload thinking.

Korean interview notes are kept in:

```text
docs/reports/korean_interview_brief.md
```

This document turns the technical work into concise speaking points, expected Q&A, resume bullet candidates, and an Obsidian TIL draft.

The repeatable run checklist is kept in:

```text
docs/reports/validation_run_checklist.md
```

It defines pre-run safety checks, test-condition fields, environment snapshot expectations, post-run output checks, metric review, and interpretation red flags.

The next experiment plan is kept in:

```text
docs/reports/stage2_next_experiment_plan.md
```

It defines the safe order for repeated 120s sustained runs, longer 300s sustained runs, read-side sustained comparison, and read-only telemetry reconnaissance.

## Stage 1 Review

Stage 1 is summarized in:

```text
docs/reports/stage1_review.md
```

This review connects the baseline, QD sweep, reproducibility, and direct/buffered experiments into one portfolio-oriented story.

## Week 8 Environment Collection

Stage 2 begins with environment collection:

```powershell
cd D:\ssd_lab
powershell -ExecutionPolicy Bypass -File .\scripts\collect_env_windows.ps1
```

The script writes machine-specific snapshots to:

```text
results/env/<timestamp>/
results/env/latest/
```

These environment snapshots are intentionally ignored by Git. The lab write-up is kept in:

```text
docs/reports/environment_collection_week8.md
```

## Week 9 WSL Path Comparison

Week 9 compares safe file-based fio behavior between WSL native ext4 and the Windows-mounted `/mnt/d` path.

Run:

```powershell
cd D:\ssd_lab
.\run_wsl_path_compare.ps1

python .\parse_fio_results.py `
  --input-dir D:\ssd_lab\results\wsl_path_compare `
  --output D:\ssd_lab\results\wsl_path_compare_summary.csv

python .\analyze_wsl_path_compare.py
```

Write-up:

```text
docs/reports/wsl_path_compare_week9.md
```

Key observation:

- WSL ext4 and `/mnt/d` behaved very differently, especially for random write.
- This is a path-level result, not raw SSD media performance.
- Future WSL fio results must label whether they came from WSL ext4 or `/mnt/d`.

## QoS and Tail Latency Review

QoS-focused summary:

```powershell
cd D:\ssd_lab
python .\analyze_qos_tail_latency.py
```

Outputs:

```text
results/qos_tail_latency_summary.csv
results/qos_tail_latency_plots/
docs/reports/qos_tail_latency_review.md
```

Key observation:

- Average IOPS is not enough for validation.
- p99, p99.9, and CV help identify unstable or path-sensitive conditions.
- Conditions with good-looking throughput may still be poor QoS candidates.

## Week 10 Sustained Workload Smoke Test

Week 10 adds a conservative sustained workload smoke test:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_SUSTAINED_LABEL = "rand_write_120s_smoke"
.\run_sustained_smoke.ps1

python .\analyze_sustained_smoke.py
```

Defaults:

```text
rand_write, 4k, iodepth=16, direct=1, size=1G, runtime=120s, repeats=1
```

Write-up:

```text
docs/reports/sustained_workload_week10.md
```

Outputs:

```text
results/sustained_smoke/
results/sustained_smoke_summary.csv
results/sustained_smoke_timeseries.csv
results/sustained_smoke_window_summary.csv
results/sustained_smoke_latency_spikes.csv
results/sustained_smoke_repeatability.csv
results/sustained_smoke_result_set_comparison.csv
results/sustained_smoke_workload_comparison.csv
results/sustained_smoke_plots/
```

New sustained runs are stored under labeled subdirectories such as:

```text
results/sustained_smoke/rand_write_120s_smoke/
```

The analyzer preserves a `result_set` column so repeated runs and longer runtime experiments can be compared without losing their source labels.

Smoke-run observation:

- Full-run throughput was 86.41 MiB/s and 22,120.82 IOPS.
- p99 completion latency was 1.58 ms, and p99.9 was 5.14 ms.
- Last-third IOPS was about 95.4% of first-third IOPS.
- Last-third average completion latency was about 4.9% higher than first-third latency.
- One max-latency outlier reached about 1.04 seconds, so future sustained runs should track outliers explicitly.
- The highest average-latency interval was 876.37 us at 11.007 seconds; this is a time-window signal, not the exact max-latency I/O.
- The 3-run repeat set had stable bandwidth/IOPS CV around 0.028, but p99.9 CV was 0.393 and max-latency CV was 1.564.
- Run 2 of the repeat set showed the largest max-latency outlier at about 4.94 seconds.
- Compared with the legacy smoke run, the 3-run repeat set had 1.339x average IOPS, 0.457x mean p99 latency, 0.305x mean p99.9 latency, and 1.695x mean max latency.
- The 300s repeat set had 77.47 MiB/s, 19,831.08 IOPS, 2.48 ms mean p99, and 9.01 ms mean p99.9.
- Compared with the 120s repeat set, the 300s repeat set had 0.670x average IOPS, 3.437x mean p99 latency, and 5.749x mean p99.9 latency.
- The 120s read repeat set had 95.88 MiB/s, 24,545.59 IOPS, 2.48 ms mean p99, and 9.85 ms mean p99.9.
- In the 120s read/write comparison, write had 1.207x average IOPS and lower p99/p99.9, but 17.316x higher mean max latency because of a rare write outlier.

## Current Limitations

- Tests are file-based, not raw block-device validation.
- The current hardware path includes Windows filesystem and, for the external SSD, USB/enclosure effects.
- Most experiments use 30 second runs; Week 10 now has write-side 120s/300s repeat sets and a read-side 120s repeat set.
- Each condition currently has only three repeated runs.
- SMART/NVMe telemetry is not collected yet.

## Next Steps

- Run read-only telemetry reconnaissance
- Compare telemetry/environment context against sustained write/read behavior
- Use the validation run checklist before each new experiment
- Refine the Korean interview brief into a public-facing portfolio README
- Obsidian TIL notes connected to this project

## Commit History Checkpoints

- `Add SSD mini-lab baseline fio analysis`
- `Add QD sweep analysis outputs`
- `Add QD sweep reproducibility analysis`
- `Add project README`
- `Add direct buffered analysis`
