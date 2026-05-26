# SSD Mini Lab

fio-based SSD validation mini-lab for learning, portfolio building, and interview preparation.

The goal is not to chase the highest benchmark number. The goal is to build a repeatable validation flow:

- define test conditions
- collect fio JSON results
- parse results into CSV
- visualize bandwidth, IOPS, and latency
- compare repeated runs
- document interpretation and limitations

## Current Status

| Area | Status | Main outputs |
|---|---|---|
| Baseline fio parsing | Done | `parse_fio_results.py`, `results/fio_summary.csv` |
| Baseline plots | Done | `plot_fio_summary.py`, `results/plots/` |
| Queue-depth sweep | Done | `analyze_qd_sweep.py`, `results/qd_sweep_grouped.csv`, `results/qd_sweep_plots/` |
| QD reproducibility | Done | `analyze_qd_reproducibility.py`, `results/qd_sweep_reproducibility.csv` |
| Week 7 direct vs buffered | Done | `analyze_direct_buffered.py`, `results/direct_buffered_*`, `results/direct_buffered_plots/` |

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

## Current Limitations

- Tests are file-based, not raw block-device validation.
- The current hardware path includes Windows filesystem and, for the external SSD, USB/enclosure effects.
- Most experiments use 30 second runs, so long sustained behavior is not covered yet.
- Each condition currently has only three repeated runs.
- SMART/NVMe telemetry is not collected yet.

## Next Steps

- Stage 1 review report for Weeks 1-7
- WSL/Linux environment collection and path comparison
- Longer sustained workload experiment
- More explicit QoS/tail-latency report
- Obsidian TIL notes connected to this project

## Commit History Checkpoints

- `Add SSD mini-lab baseline fio analysis`
- `Add QD sweep analysis outputs`
- `Add QD sweep reproducibility analysis`
- `Add project README`
- `Add direct buffered analysis`
