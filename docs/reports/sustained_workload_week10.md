# Week 10 - Sustained Workload Smoke Test

## Purpose

Week 10 starts the sustained workload track.

The goal is not to immediately run a destructive long-duration benchmark. The first step is a conservative smoke test that verifies:

- fio can run longer than the previous 15-30 second tests
- output JSON is generated correctly
- time-series logs can be collected
- the test remains file-based and safe

## Safety Boundary

This lab uses a regular file only:

```text
D:\ssd_lab\fio_testfile_sustained_smoke
```

It does not target raw devices such as:

```text
\\.\PhysicalDriveN
/dev/sdX
/dev/nvmeXnY
```

## Default Test

| Parameter | Default |
|---|---:|
| workload | `rand_write` |
| rw | `randwrite` |
| block size | `4k` |
| iodepth | `16` |
| size | `1G` |
| runtime | `120s` |
| direct | `1` |
| repeats | `1` |
| log interval | `1000 ms` |

This is intentionally small. It is a smoke test, not a final sustained validation run.

## Run

```powershell
cd D:\ssd_lab
.\run_sustained_smoke.ps1
```

Optional overrides:

```powershell
$env:SSD_LAB_SUSTAINED_RUNTIME = "300"
$env:SSD_LAB_SUSTAINED_SIZE = "2G"
$env:SSD_LAB_SUSTAINED_RUNS = "3"
$env:SSD_LAB_SUSTAINED_LABEL = "rand_write_300s_repeat3"
.\run_sustained_smoke.ps1
```

New runs are written into a labeled subdirectory:

```text
results/sustained_smoke/<label>/
```

If `SSD_LAB_SUSTAINED_LABEL` is not set, the script derives a label from workload, runtime, size, block size, queue depth, and direct mode.

## Analysis

```powershell
cd D:\ssd_lab
python .\analyze_sustained_smoke.py
```

Outputs:

| Output | Meaning |
|---|---|
| `results/sustained_smoke/` | fio JSON and time-series logs |
| `results/sustained_smoke_summary.csv` | per-run fio summary |
| `results/sustained_smoke_timeseries.csv` | normalized time-series samples |
| `results/sustained_smoke_window_summary.csv` | first/middle/last window summary |
| `results/sustained_smoke_latency_spikes.csv` | highest average-latency intervals per run |
| `results/sustained_smoke_repeatability.csv` | run-to-run repeatability summary |
| `results/sustained_smoke_result_set_comparison.csv` | pairwise comparison between result sets |
| `results/sustained_smoke_workload_comparison.csv` | read/write comparison under matching conditions |
| `results/sustained_smoke_plots/` | IOPS, bandwidth, and latency trend plots |

The analyzer preserves `result_set` so repeated 120s, longer 300s, and read-side result sets can be compared without mixing their source folders.

Plots:

- [IOPS over time](../../results/sustained_smoke_plots/sustained_iops_over_time.png)
- [Bandwidth over time](../../results/sustained_smoke_plots/sustained_bandwidth_over_time.png)
- [Average completion latency over time](../../results/sustained_smoke_plots/sustained_clat_avg_over_time.png)

## Why This Comes After QoS Review

The QoS review showed that short tests can already expose p99 and p99.9 differences, but they do not show whether latency changes over time.

A sustained workload asks a different question:

> Does the device/path remain stable as the workload continues?

Possible sustained-run signals:

- throughput decline
- IOPS decline
- p99 or p99.9 growth
- sudden latency spikes
- increased run-to-run variation
- path/cache behavior changing after warm-up

## Smoke Result

Run date: 2026-06-07

Aggregate result:

| Workload | Runtime | BW (MiB/s) | IOPS | Mean clat (us) | p99 clat (us) | p99.9 clat (us) | Max clat (us) |
|---|---:|---:|---:|---:|---:|---:|---:|
| rand_write, 4k, QD16, direct=1 | 120s | 86.41 | 22,120.82 | 367.29 | 1,581.06 | 5,144.58 | 1,040,586.91 |

Window comparison:

| Window | Time range (s) | Avg BW (MiB/s) | Avg IOPS | Avg clat (us) |
|---|---:|---:|---:|---:|
| first third | 1.049-40.000 | 91.24 | 23,358.41 | 370.00 |
| middle | 41.000-80.000 | 83.32 | 21,329.78 | 414.79 |
| last third | 81.000-120.031 | 87.02 | 22,278.05 | 388.23 |

First-vs-last ratios:

| Metric | Last / First |
|---|---:|
| IOPS | 0.954 |
| Bandwidth | 0.954 |
| Average completion latency | 1.049 |

Highest average-latency intervals:

| Rank | Time (s) | Avg clat (us) | Robust z-score | Candidate spike |
|---:|---:|---:|---:|---|
| 1 | 11.007 | 876.37 | 5.53 | yes |
| 2 | 69.000 | 729.49 | 3.96 | yes |
| 3 | 55.000 | 723.89 | 3.90 | yes |
| 4 | 17.002 | 688.33 | 3.52 | yes |
| 5 | 91.000 | 666.01 | 3.29 | no |

## Repeat 120s Result

Result set: `rand_write_120s_repeat3`

Run date: 2026-06-07

Per-run summary:

| Run | BW (MiB/s) | IOPS | Mean clat (us) | p99 clat (us) | p99.9 clat (us) | Max clat (us) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 119.32 | 30,544.77 | 271.85 | 684.03 | 1,236.99 | 309,813.69 |
| 2 | 114.72 | 29,367.50 | 284.54 | 675.84 | 1,187.84 | 4,944,516.04 |
| 3 | 113.08 | 28,948.27 | 285.61 | 806.91 | 2,277.38 | 36,240.11 |

Repeatability summary:

| Metric | Mean | CV |
|---|---:|---:|
| Bandwidth | 115.70 MiB/s | 0.028 |
| IOPS | 29,620.18 | 0.028 |
| Mean clat | 280.67 us | 0.027 |
| p99 clat | 722.26 us | 0.102 |
| p99.9 clat | 1,567.40 us | 0.393 |
| Max clat | 1,763,523.28 us | 1.564 |
| First/last IOPS ratio | 1.073 | 0.099 |
| First/last avg clat ratio | 1.063 | 0.325 |

First-vs-last ratios:

| Run | IOPS last/first | Avg clat last/first |
|---:|---:|---:|
| 1 | 1.075 | 0.911 |
| 2 | 0.965 | 1.458 |
| 3 | 1.178 | 0.820 |

Result-set comparison:

| Base | Compare | IOPS ratio | p99 ratio | p99.9 ratio | Max latency ratio |
|---|---|---:|---:|---:|---:|
| legacy_root | rand_write_120s_repeat3 | 1.339 | 0.457 | 0.305 | 1.695 |

## Repeat 300s Result

Result set: `rand_write_300s_repeat3`

Run date: 2026-06-08

Per-run summary:

| Run | BW (MiB/s) | IOPS | Mean clat (us) | p99 clat (us) | p99.9 clat (us) | Max clat (us) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 83.97 | 21,497.29 | 379.57 | 1,679.36 | 6,324.22 | 2,145,048.36 |
| 2 | 75.25 | 19,264.44 | 427.25 | 2,736.13 | 10,682.37 | 68,495.73 |
| 3 | 73.17 | 18,731.53 | 439.80 | 3,031.04 | 10,027.01 | 70,828.12 |

Repeatability summary:

| Metric | Mean | CV |
|---|---:|---:|
| Bandwidth | 77.47 MiB/s | 0.074 |
| IOPS | 19,831.08 | 0.074 |
| Mean clat | 415.54 us | 0.076 |
| p99 clat | 2,482.18 us | 0.286 |
| p99.9 clat | 9,011.20 us | 0.261 |
| Max clat | 761,457.40 us | 1.574 |
| First/last IOPS ratio | 1.263 | 0.259 |
| First/last avg clat ratio | 0.806 | 0.258 |

120s-vs-300s result-set comparison:

| Base | Compare | IOPS ratio | p99 ratio | p99.9 ratio | Max latency ratio |
|---|---|---:|---:|---:|---:|
| rand_write_120s_repeat3 | rand_write_300s_repeat3 | 0.670 | 3.437 | 5.749 | 0.432 |

## Repeat Read 120s Result

Result set: `rand_read_120s_repeat3`

Run date: 2026-06-08

Per-run summary:

| Run | BW (MiB/s) | IOPS | Mean clat (us) | p99 clat (us) | p99.9 clat (us) | Max clat (us) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 105.66 | 27,049.21 | 383.86 | 1,744.90 | 9,240.58 | 88,486.11 |
| 2 | 95.32 | 24,401.21 | 416.46 | 2,539.52 | 9,109.50 | 102,640.47 |
| 3 | 86.67 | 22,186.35 | 453.84 | 3,162.11 | 11,206.66 | 114,400.63 |

Repeatability summary:

| Metric | Mean | CV |
|---|---:|---:|
| Bandwidth | 95.88 MiB/s | 0.099 |
| IOPS | 24,545.59 | 0.099 |
| Mean clat | 418.06 us | 0.084 |
| p99 clat | 2,482.18 us | 0.286 |
| p99.9 clat | 9,852.25 us | 0.119 |
| Max clat | 101,842.40 us | 0.127 |
| First/last IOPS ratio | 1.148 | 0.089 |
| First/last avg clat ratio | 0.859 | 0.071 |

120s read-vs-write comparison:

| Base | Compare | IOPS ratio | p99 ratio | p99.9 ratio | Max latency ratio |
|---|---|---:|---:|---:|---:|
| rand_read_120s_repeat3 | rand_write_120s_repeat3 | 1.207 | 0.291 | 0.159 | 17.316 |

## Interpretation

The sustained smoke structure worked: fio produced JSON plus time-series logs, and the analyzer generated summary CSVs and plots.

The 120 second smoke run did not show a catastrophic throughput drop. Last-third IOPS was about 95.4% of first-third IOPS, and last-third bandwidth showed the same ratio.

Average completion latency increased mildly in the last third, from about 370 us to 388 us. The full-run p99 was 1.58 ms and p99.9 was 5.14 ms.

The maximum completion latency was about 1.04 seconds. This is a clear outlier worth tracking, but one smoke run is not enough to decide whether it came from SSD behavior, filesystem activity, OS scheduling, background load, or fio/file allocation effects.

The time-series latency-spike table uses interval average completion latency, not per-I/O maximum latency. That means it can show suspicious time windows, but it cannot pinpoint the exact 1.04 second max-latency I/O from the JSON summary. This distinction matters: aggregate max latency and interval average latency answer related but different validation questions.

The three-run repeat set shows why repeatability matters. Bandwidth and IOPS were relatively stable, with CV around 2.8%. Tail behavior was much less stable: p99.9 CV was 39.3%, and max-latency CV was 156.4%.

Run 2 had the largest max-latency outlier at about 4.94 seconds and a high average-latency spike near 102 seconds. This should be documented as an outlier observation, not as proof of an internal SSD cause.

The result-set comparison also shows that better average throughput does not automatically mean better worst-case behavior. The repeat set had about 1.34x higher average IOPS than the legacy smoke run and lower mean p99/p99.9 latency, but its mean max latency was about 1.70x higher because of the run 2 outlier.

The 300 second repeat set changed the sustained interpretation. Compared with the 120 second repeat set, average IOPS dropped to about 67.0%, while mean p99 latency increased by about 3.44x and mean p99.9 latency increased by about 5.75x. This suggests the longer runtime exposed worse tail-latency behavior in this file-based test path.

The 300 second set did not have a larger mean max latency than the 120 second set, mainly because the 120 second run 2 had a very large max-latency outlier. This is another reminder that max latency is sensitive to rare events and should be reviewed alongside p99/p99.9 and time-series spike candidates.

The 120 second read/write comparison showed another useful validation pattern. The write set had about 1.21x higher average IOPS than the read set and much lower mean p99/p99.9 latency. However, write-side mean max latency was about 17.3x higher because of the large write outlier. This again separates steady/tail percentile behavior from rare worst-case behavior.

## Interpretation Rules

Do not over-interpret the first smoke run.

The first run proves that the sustained test structure works. Stronger conclusions require:

- more repeats
- longer runtime
- environment snapshot before the run
- comparison against previous short-run results
- careful labeling of path and direct mode
- outlier review for max latency spikes

## Current Status

First sustained smoke run, three-run 120 second write repeat set, three-run 300 second write repeat set, and three-run 120 second read repeat set completed.

Next analysis step: add read-only telemetry to explain path-level changes more carefully, or run a longer read-side sustained set if a symmetric read/write duration comparison is needed.
