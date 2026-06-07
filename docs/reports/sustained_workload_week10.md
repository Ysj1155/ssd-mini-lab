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
.\run_sustained_smoke.ps1
```

## Expected Outputs

```text
results/sustained_smoke/
```

Expected output types:

| Output | Meaning |
|---|---|
| `*_sustained_run*.json` | fio JSON result |
| `*_bw*.log` | bandwidth time-series log |
| `*_iops*.log` | IOPS time-series log |
| `*_lat*.log` | latency time-series log |

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

## Interpretation Rules

Do not over-interpret the first smoke run.

The first run only proves that the sustained test structure works. Stronger conclusions require:

- more repeats
- longer runtime
- environment snapshot before the run
- comparison against previous short-run results
- careful labeling of path and direct mode

## Next Analysis Step

After a successful smoke run, add an analyzer that reads fio time-series logs and reports:

- average IOPS by time window
- p95/p99-like latency trend if log format supports it
- first third vs last third comparison
- visible latency spike points

## Current Status

Ready to run.
