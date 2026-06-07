# Validation Run Checklist

## Purpose

This checklist is used before and after each SSD mini-lab experiment.

The goal is to make each run explainable, repeatable, and safe. A result is useful only when the test condition, environment, output files, and interpretation boundary are clear.

## Pre-Run Checklist

### 1. Safety Boundary

- Confirm the test targets a regular file, not a raw disk device.
- Confirm the test file path is inside the intended workspace or WSL test directory.
- Confirm the run script does not point to `\\.\PhysicalDriveN`, `/dev/sdX`, or `/dev/nvmeXnY`.
- Confirm the target drive has enough free space for the planned test file.

### 2. Test Condition

Record these before running:

| Field | Example |
|---|---|
| workload | `rand_write` |
| rw | `randwrite` |
| block size | `4k` |
| queue depth | `16` |
| direct mode | `1` |
| runtime | `120s` |
| size | `1G` |
| repeat count | `3` |
| path | `D:\ssd_lab`, WSL ext4, or `/mnt/d` |
| tool version | `fio-3.42` |

### 3. Environment Snapshot

- Run the Windows environment collection script for major experiments.
- If WSL is involved, capture WSL version, kernel, distribution, `lsblk`, and `df -h`.
- Record whether the test ran on Windows path, WSL native ext4, or `/mnt/d`.
- Note any unusual background load, low disk space, thermal concern, or system update activity.

### 4. Expected Outputs

Before running, know what files should be produced:

- fio JSON files
- parser CSV
- grouped or comparison CSV
- plots
- report markdown

If the output name does not encode the workload and run number, fix the naming before trusting the result.

## Post-Run Checklist

### 1. Output Completeness

- Confirm every planned run produced a JSON result.
- Confirm every JSON result was parsed into CSV.
- Confirm plots were regenerated after CSV changes.
- Confirm report links point to existing files.

### 2. Metadata Integrity

Check that parsed results preserve:

- workload
- run number
- QD or iodepth
- direct mode
- runtime
- block size
- path or test mode
- fio version when available

### 3. Metric Review

Review more than average throughput:

- bandwidth
- IOPS
- mean latency
- p95 latency
- p99 latency
- p99.9 latency
- max latency
- CV or run-to-run variation
- first-vs-last sustained window ratio if time-series data exists

### 4. Interpretation Boundary

Before writing a conclusion, answer:

- Is this result path-level, filesystem-level, or device-level?
- Could OS cache affect the result?
- Could WSL or `/mnt/d` path behavior affect the result?
- Is the run count enough to discuss reproducibility?
- Is runtime long enough to discuss sustained behavior?
- Is telemetry available, or are internal SSD causes only speculation?

### 5. Report Update

Each completed experiment should leave behind:

- run command
- input and output paths
- key table
- plot links
- short interpretation
- limitations
- next action

## Red Flags

Treat these as reasons to pause interpretation:

- only one run for a condition that needs reproducibility
- missing environment snapshot
- output file names do not encode workload/run condition
- direct mode is unclear
- Windows and WSL path results are mixed without labels
- p99 or p99.9 gets worse while average IOPS looks good
- max latency outlier appears but no follow-up plan exists
- report claims internal SSD causes without telemetry

## Interview Framing

Useful sentence:

> I treated the benchmark as a validation experiment, so I checked safety, test conditions, environment, metadata, QoS metrics, and interpretation limits before trusting the numbers.

This checklist is meant to show that the project is not only about running fio. It is about building test discipline.
