# External SSD DUT Profile

This document defines the external SSD as a black-box DUT (Device Under Test).

The purpose is to make each fio run traceable to a concrete product path and environment. This is not an internal FTL/GC model.

## DUT Identity

| Field | Value |
|---|---|
| DUT label | `external_ssd_dut_01` |
| Vendor / model | SanDisk Extreme SSD |
| Capacity | About 1 TB as currently reported by Windows; earlier notes should be rechecked before public wording |
| Serial number | Optional / do not publish if sensitive |
| Connection | External SSD over USB path |
| Enclosure / adapter | TBD |
| Host port | TBD |
| File system | exFAT |
| Volume label | `Extreme SSD` |
| Test file path | `E:\validation\ssd_lab_fio_testfile` |
| Identity enrollment | `configs/external_ssd_dut_identity.json` |
| Stored device fingerprint | SHA-256 only; raw serial is not stored or returned |
| Actual read-only preflight | Pass on 2026-07-27 |
| Preflight evidence | `results/external_ssd/dut_preflight_readonly_20260727/preflight.json` |

## Host Environment

| Field | Value |
|---|---|
| Host OS | Windows |
| fio version | TBD |
| Python version | TBD |
| Shell | PowerShell |
| Repo path | `D:\ssd_lab` |
| Environment snapshot | `results/env/latest/` after collection |
| Telemetry snapshot | `results/telemetry/latest/` after collection |

## Validation Scope

In scope:

- fio-based file target testing
- throughput, IOPS, p99, p99.9, and max latency review
- repeated-run variation
- sustained workload behavior
- environment and telemetry snapshots
- black-box interpretation of observable behavior

Out of scope:

- raw physical-drive destructive tests
- firmware modification
- direct NAND/FTL/GC tracing
- power-rail measurement unless external measurement equipment is added

## Interpretation Boundary

This DUT is tested through an external path. Results may include effects from:

- USB bridge or enclosure
- host controller
- Windows filesystem
- OS cache and scheduler behavior
- fio file allocation and test-file reuse

Therefore, this project can support product-like black-box validation observations, but it should not claim direct NAND, FTL, or GC root cause without additional evidence.

## Pre-Run Checklist

- Confirm the intended physical USB port.
- Run only through an external SSD runner that loads `ExternalSsdSafety.psm1`.
- Require canonical target containment under the enrolled allowed root.
- Require volume GUID, label, filesystem, capacity, model, USB bus, and hashed
  disk fingerprint to match `external_ssd_dut_identity.json`.
- Refuse boot/system disks, reparse-point paths, UNC/device paths, and alternate
  data streams.
- Confirm free space is sufficient for the selected test size.
- Close unrelated heavy background applications.
- Collect environment snapshot.
- Collect storage telemetry snapshot if permissions allow.
- Record any device temperature / SMART data available before the run.

The actual-DUT check is independently reproducible with
`scripts/observers/check_external_ssd_dut_preflight.ps1`. It validates an
existing target and emits JSON to stdout without launching fio or modifying
the target.
