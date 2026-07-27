# External SSD Validation Roadmap

## 1. Direction

The performance-characterization phase is mature enough to stop adding broad
parameter sweeps.

Completed evidence now covers:

- queue depth
- direct versus buffered I/O
- sustained runtime and tail latency
- reconnect-start state comparisons
- large working set sequential behavior
- mixed workload controls and counterbalanced ratios
- idle-duration sensitivity
- controlled 4K/64K/1M block-size mapping
- runner/observer separation and integrated manifests

The next project phase should turn this from a benchmark collection into a
small black-box product-validation system:

```text
measured performance
-> correctness and recovery
-> observability-assisted diagnosis
-> requirement-based regression
-> concise portfolio delivery
```

This remains separate from the FTL white-box project. It validates externally
observable product behavior and does not model internal mapping, GC, or NAND.

## 2. Next MVP: File-Target Data Integrity

Completion status: the retry1 evidence passed the 4 GiB CRC32C write/readback requirement. See `external_ssd_data_integrity_result.md`.

Proposed protocol: `EXT-DATA-INTEGRITY-001`

Question:

> Can a dedicated external-SSD file be written and verified with deterministic
> data patterns while preserving machine-readable pass/fail evidence?

Safe MVP scope:

- separate dedicated verification file under `E:\validation`
- conservative 4 GiB file size
- fio file target, never a physical drive
- deterministic verify pattern or checksum
- write phase followed by read/verify phase
- JSON output, exit code, verification error count, and manifest
- one positive execution plus parser tests for a synthetic verification error

MVP completion criteria:

- verification file and byte count are explicit
- fio reports zero verification errors for the real run
- analyzer produces an unambiguous `Pass` or `Fail`
- a fixture proves that the analyzer rejects a verification-error result
- report states that this is file-target integrity, not power-loss protection

This adds correctness evidence without destructive raw-device access or forced
power interruption.

## 3. Follow-On: Safe Recovery Behavior

Only after the integrity MVP is stable:

- application-level interruption against a disposable dedicated file
- remount/reconnect availability checks without claiming power-loss coverage
- post-reconnect checksum/verify
- explicit distinction between expected incomplete writes and silent
  corruption

Unsafe scope remains excluded:

- forced power removal during writes
- raw-device writes
- format, trim, firmware changes, or namespace operations

These require separate hardware, safety review, and recovery planning.

## 4. Observability Upgrade

Execution status: the first synchronized collectors ran, but all samples were zero while fio was active. Host-side evidence is Limited; the limitation is preserved rather than treated as diagnostic coverage.

Current pre/post observation is useful but cannot explain transient behavior.
The next observer upgrade should collect synchronized, read-only host evidence
during fio when available:

- target volume identity and USB topology
- Windows logical/physical disk counters
- queue length, bytes/sec, and response-time counters
- timestamp alignment with fio one-second logs
- collection failures recorded as `limited`

SMART and device reliability counters remain optional because the USB bridge
and Windows access path may not expose them.

The objective is correlation, not automatic root-cause claims.

## 5. Requirement-Based Regression

After integrity and observer MVPs:

- define a small release-style profile from existing stable conditions
- separate evidence requirements from performance thresholds
- use baseline bands only after enough independent sessions exist
- retain p99/p99.9 and maximum-latency anomalies
- run parser/analyzer tests in CI
- generate one validation summary from manifests rather than hand-copying
  results

A useful minimal profile would contain:

- 4K random read/write at QD1 and QD16
- 64K random read/write at QD32
- one 120-second sustained QoS condition
- one file-integrity verification condition

## 6. Portfolio Delivery

The final portfolio should be smaller than the repository:

1. An on-request delivery README with project objective, DUT boundary, and validation flow.
2. One condition table showing controlled variables.
3. One fio JSON-to-CSV evidence flow.
4. Three case studies:
   - QD and tail-latency tradeoff
   - a hypothesis that failed to reproduce
   - 64K block-size throughput knee
5. One data-integrity pass/fail case after the MVP completes.
6. A limitations section covering USB, Windows, exFAT, file target, telemetry,
   and unavailable power validation.

## 7. Priority Order

1. Completed: close the controlled block-size result and update portfolio evidence.
2. Completed: `EXT-DATA-INTEGRITY-001` passed the file-target CRC32C requirement.
3. Completed with limitation: synchronized logical-disk evidence was produced but classified Limited.
4. Contract complete: compact regression YAML, verdict separation, and manifest-only analyzer are defined; no workload has been run.
5. Deferred: create Korean portfolio and interview material only when explicitly requested.

Do not add another broad performance sweep unless a requirement or a specific
debug question justifies it.
