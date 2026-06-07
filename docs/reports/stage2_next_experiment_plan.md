# Stage 2 Next Experiment Plan

## Purpose

This plan defines the next safe experiments after the first sustained workload smoke run.

The goal is to move from "one successful sustained run" to "repeatable sustained validation evidence" without jumping into unsafe raw-device testing.

## Current Baseline For Stage 2

Completed:

- environment collection
- WSL path comparison
- QoS and tail-latency review
- one sustained randwrite smoke run
- three-run 120 second sustained randwrite repeat set
- three-run 300 second sustained randwrite repeat set
- three-run 120 second sustained randread repeat set
- sustained time-series analysis
- latency-spike candidate extraction

Current sustained repeat results:

| Metric | Value |
|---|---:|
| workload | rand_write |
| block size | 4k |
| iodepth | 16 |
| direct | 1 |
| 120s bandwidth mean | 115.70 MiB/s |
| 120s IOPS mean | 29,620.18 |
| 120s p99 clat mean | 0.72 ms |
| 120s p99.9 clat mean | 1.57 ms |
| 300s bandwidth mean | 77.47 MiB/s |
| 300s IOPS mean | 19,831.08 |
| 300s p99 clat mean | 2.48 ms |
| 300s p99.9 clat mean | 9.01 ms |
| 300s/120s IOPS ratio | 0.670 |
| 300s/120s p99 ratio | 3.437 |
| 300s/120s p99.9 ratio | 5.749 |
| 120s read IOPS mean | 24,545.59 |
| 120s read p99 clat mean | 2.48 ms |
| 120s read p99.9 clat mean | 9.85 ms |
| 120s write/read IOPS ratio | 1.207 |
| 120s write/read p99 ratio | 0.291 |
| 120s write/read p99.9 ratio | 0.159 |

## Experiment 1 - Repeat Sustained Smoke

### Question

Does the 120 second sustained smoke result repeat, or was the first run unusually good or bad?

### Status

Completed on 2026-06-07.

### Command

```powershell
cd D:\ssd_lab

$env:SSD_LAB_SUSTAINED_RUNTIME = "120"
$env:SSD_LAB_SUSTAINED_SIZE = "1G"
$env:SSD_LAB_SUSTAINED_RUNS = "3"
$env:SSD_LAB_SUSTAINED_WORKLOAD = "rand_write"
$env:SSD_LAB_SUSTAINED_RW = "randwrite"
$env:SSD_LAB_SUSTAINED_BS = "4k"
$env:SSD_LAB_SUSTAINED_IODEPTH = "16"
$env:SSD_LAB_SUSTAINED_DIRECT = "1"
$env:SSD_LAB_SUSTAINED_LABEL = "rand_write_120s_repeat3"

powershell -ExecutionPolicy Bypass -File .\scripts\collect_env_windows.ps1
.\run_sustained_smoke.ps1
python .\analyze_sustained_smoke.py
```

### Review Metrics

- run-to-run bandwidth variation
- run-to-run IOPS variation
- p99 and p99.9 variation
- max latency per run
- latency-spike candidate count per run
- first-vs-last IOPS ratio
- first-vs-last average latency ratio

### Pass Criteria

This experiment is strong enough to move forward if:

- all three runs complete
- all expected JSON/log/CSV/plot outputs are generated
- no run has missing metadata
- p99 and p99.9 are explainable and not wildly inconsistent without a note
- max-latency outliers are documented instead of ignored

### Result

All three runs completed and were analyzed under result set `rand_write_120s_repeat3`.

Summary:

- bandwidth/IOPS CV was about 0.028
- p99 latency CV was about 0.102
- p99.9 latency CV was about 0.393
- max-latency CV was about 1.564
- run 2 showed a max-latency outlier of about 4.94 seconds

Decision:

Proceed to Experiment 2 only with the interpretation that average throughput was repeatable, while tail latency and max-latency behavior still need caution.

## Experiment 2 - Longer Sustained Smoke

### Question

Does the workload remain stable when runtime increases beyond the initial smoke duration?

### Status

Completed on 2026-06-08.

### Proposed Command

```powershell
cd D:\ssd_lab

$env:SSD_LAB_SUSTAINED_RUNTIME = "300"
$env:SSD_LAB_SUSTAINED_SIZE = "2G"
$env:SSD_LAB_SUSTAINED_RUNS = "3"
$env:SSD_LAB_SUSTAINED_WORKLOAD = "rand_write"
$env:SSD_LAB_SUSTAINED_RW = "randwrite"
$env:SSD_LAB_SUSTAINED_BS = "4k"
$env:SSD_LAB_SUSTAINED_IODEPTH = "16"
$env:SSD_LAB_SUSTAINED_DIRECT = "1"
$env:SSD_LAB_SUSTAINED_LABEL = "rand_write_300s_repeat3"

powershell -ExecutionPolicy Bypass -File .\scripts\collect_env_windows.ps1
.\run_sustained_smoke.ps1
python .\analyze_sustained_smoke.py
```

### Review Metrics

- first/middle/last window behavior
- p99 and p99.9 latency growth
- max-latency outliers
- sustained IOPS trend
- sustained bandwidth trend
- latency-spike timing pattern
- result-set comparison ratios against `rand_write_120s_repeat3`

### Pass Criteria

The longer test is useful if:

- results can be compared against the 120 second repeat set
- output naming clearly separates 120s and 300s runs
- latency outliers are described without claiming internal SSD causes
- the report states whether the longer run changed the interpretation

### Result

All three 300 second runs completed and were analyzed under result set `rand_write_300s_repeat3`.

Summary:

- bandwidth/IOPS CV was about 0.074
- p99 latency CV was about 0.286
- p99.9 latency CV was about 0.261
- max-latency CV was about 1.574
- compared with the 120 second repeat set, average IOPS dropped to 0.670x
- compared with the 120 second repeat set, mean p99 increased to 3.437x
- compared with the 120 second repeat set, mean p99.9 increased to 5.749x

Decision:

The 300 second set shows materially worse sustained tail-latency behavior than the 120 second set. Proceed to read-side sustained comparison or read-only telemetry rather than increasing write runtime again immediately.

## Experiment 3 - Read-Side Sustained Smoke

### Question

Does sustained random read show a different stability pattern than sustained random write?

### Status

Completed on 2026-06-08.

### Proposed Command

```powershell
cd D:\ssd_lab

$env:SSD_LAB_SUSTAINED_RUNTIME = "120"
$env:SSD_LAB_SUSTAINED_SIZE = "1G"
$env:SSD_LAB_SUSTAINED_RUNS = "3"
$env:SSD_LAB_SUSTAINED_WORKLOAD = "rand_read"
$env:SSD_LAB_SUSTAINED_RW = "randread"
$env:SSD_LAB_SUSTAINED_BS = "4k"
$env:SSD_LAB_SUSTAINED_IODEPTH = "16"
$env:SSD_LAB_SUSTAINED_DIRECT = "1"
$env:SSD_LAB_SUSTAINED_LABEL = "rand_read_120s_repeat3"

powershell -ExecutionPolicy Bypass -File .\scripts\collect_env_windows.ps1
.\run_sustained_smoke.ps1
python .\analyze_sustained_smoke.py
```

### Review Metrics

- read vs write IOPS
- read vs write p99 and p99.9
- read vs write max latency
- first-vs-last stability ratio
- latency-spike candidate pattern

### Result

All three 120 second random-read runs completed and were analyzed under result set `rand_read_120s_repeat3`.

Summary:

- bandwidth/IOPS CV was about 0.099
- p99 latency CV was about 0.286
- p99.9 latency CV was about 0.119
- max-latency CV was about 0.127
- compared with the 120 second write set, write-side average IOPS was 1.207x higher
- compared with the 120 second read set, write-side mean p99 was 0.291x and mean p99.9 was 0.159x
- write-side mean max latency was 17.316x higher than read-side mean max latency because of a rare write outlier

Decision:

The read/write comparison is complete for the 120 second condition. Proceed to read-only telemetry reconnaissance before adding more workload variants.

## Experiment 4 - Safe Telemetry Recon

### Question

Can the lab collect non-destructive device/environment telemetry that improves interpretation?

### Safe Scope

Allowed:

- OS version
- fio version
- disk free space
- WSL version
- filesystem path label
- SMART/NVMe information only if collected read-only

Not allowed in this lab without a separate safety review:

- raw-device fio writes
- destructive trim/format experiments
- physical-drive targets
- firmware-level changes

### Pass Criteria

Telemetry is useful only if:

- collection is read-only
- commands are documented
- output is stored separately from benchmark CSVs
- interpretation stays within what the telemetry can prove

## Decision Gates

| Gate | Move forward if... |
|---|---|
| Repeat 120s smoke | done; three runs completed and variation is documented |
| Longer 300s smoke | done; longer runtime reduced average IOPS and worsened p99/p99.9 latency |
| Read-side sustained smoke | done; 120s read/write behavior is documented |
| Telemetry recon | next; commands must be confirmed read-only and safe |

## Result Labeling

`run_sustained_smoke.ps1` writes each new result set into a labeled subdirectory under:

```text
results/sustained_smoke/<label>/
```

The label can be set with:

```powershell
$env:SSD_LAB_SUSTAINED_LABEL = "rand_write_120s_repeat3"
```

If no label is provided, the script derives one from workload, runtime, size, block size, queue depth, and direct mode.

The analyzer reads both legacy root-level outputs and labeled subdirectories. In CSV output, `result_set` identifies which result folder each row came from.

The analyzer also writes:

```text
results/sustained_smoke_result_set_comparison.csv
```

This file compares result sets pairwise. Use it to compare `rand_write_120s_repeat3` and `rand_write_300s_repeat3` for:

- IOPS ratio
- p99 latency ratio
- p99.9 latency ratio
- max-latency ratio
- first-vs-last ratio changes

For read/write comparison, the analyzer writes:

```text
results/sustained_smoke_workload_comparison.csv
```

This file compares matching conditions across workloads. The current 120 second read/write comparison uses the same block size, queue depth, size, direct mode, runtime, and run count.

## Portfolio Framing

Useful interview sentence:

> After the first sustained smoke run, I did not immediately treat the result as a conclusion. I planned repeated runs, longer runtime, read/write comparison, and safe telemetry collection so the evidence could become more reproducible and explainable.

## Immediate Next Action

Run Experiment 4:

```powershell
cd D:\ssd_lab
powershell -ExecutionPolicy Bypass -File .\scripts\collect_env_windows.ps1
```

Then update:

- `docs/reports/environment_collection_week8.md`
- `docs/reports/sustained_workload_week10.md`
- `docs/reports/stage2_next_experiment_plan.md`
