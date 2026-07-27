# Synchronized Windows Host Counter Observer

Implementation: `scripts/observers/collect_windows_storage_counters.ps1`

## Purpose

The existing observer captures environment and telemetry snapshots before and
after a run. This collector adds read-only host evidence during an individual
fio phase so that transient fio behavior can be compared on the same timeline.

The data is evidence for correlation. It is not automatic root-cause proof.

## Collected Fields

The collector samples the target logical-disk instance from
`Win32_PerfFormattedData_PerfDisk_LogicalDisk`:

- total, read, and write bytes per second
- reads and writes per second
- average seconds per read and write
- current disk queue length
- percent disk time
- ISO timestamp and elapsed milliseconds

It also records target volume identity, requested interval, observed duration,
sample count, and stop reason.

## Synchronization Model

For each fio phase, the runner:

1. launches the observer in a hidden PowerShell process
2. waits two seconds for initial sampling
3. runs fio
4. writes a phase-specific stop sentinel
5. waits for the observer manifest

The observer CSV and fio one-second logs therefore overlap in wall-clock time.
They remain separate evidence producers linked by `run_id` and phase name.

## Failure Behavior

Counter or CIM access can vary with Windows configuration and permissions. The
collector therefore:

- records individual query errors
- emits `limited` if no sample or no nonzero workload-activity sample was produced
- exits successfully so observation failure cannot abort the storage workload
- never treats zero-valued provider output as usable synchronized evidence

The fio runner still records the phase and the observer manifest path. Analysis
reports integrity/performance verdicts separately from observer coverage.

## Limits

Logical-disk counters include the Windows, filesystem, USB, bridge, and device
path. They cannot identify internal SSD firmware, NAND, FTL, GC, thermal, or
power causes. Physical-disk/SMART evidence remains optional when the USB bridge
does not expose it.
