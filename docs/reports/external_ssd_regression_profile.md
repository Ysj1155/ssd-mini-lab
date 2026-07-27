# Compact External SSD Regression Profile

## 1. Purpose

`EXT-REGRESSION-COMPACT-001` converts stable characterization conditions into
a small requirement-based regression contract. It does not broaden the
performance sweep and does not claim internal FTL, cache, GC, NAND, or
firmware behavior.

This design stage does not run fio. The user remains responsible for any
future external-SSD workload execution.

## 2. Traceability

```text
REQ-REG-011
-> configs/external_ssd_regression_profile.yaml
-> existing component test cases
-> component run_manifest.json files
-> evidence index
-> analyze_external_ssd_regression.py
-> component summary and independent verdict dimensions
```

The profile reuses existing test cases rather than defining new exploratory
workloads.

| Regression component | Existing condition | Repeats | Role |
|---|---|---:|---|
| `REG-PERF-RR-4K-QD1` | 4K random read, QD1, 30s | 3 | Low-QD read response |
| `REG-PERF-RR-4K-QD16` | 4K random read, QD16, 30s | 3 | Parallel read response and QoS |
| `REG-PERF-RW-4K-QD1` | 4K random write, QD1, 30s | 3 | Low-QD write response |
| `REG-PERF-RW-4K-QD16` | 4K random write, QD16, 30s | 3 | Parallel write response and QoS |
| `REG-PERF-RR-64K-QD32` | 64K random read, QD32, 30s | 3 | Observed read throughput knee |
| `REG-PERF-RW-64K-QD32` | 64K random write, QD32, 30s | 3 | Observed write throughput knee |
| `REG-QOS-RW-4K-QD16-120S` | 4K random write, QD16, 120s | 3 | Sustained windows and tail latency |
| `REG-DATA-CRC32C-4G` | 4 GiB CRC32C write/readback | 1 | File-target data-path correctness |

## 3. Threshold Policy

The initial profile uses `threshold_mode: observation`.

Existing characterization results may be shown as references, but they are
not hard release bands. Performance thresholds should be promoted only after
enough independently initiated regression sessions exist to estimate normal
variation. A future threshold revision must preserve its baseline source,
sample count, statistic, tolerance, and version in machine-readable form.

Until then:

- missing required evidence is `Blocked`
- CRC32C or fio correctness failure is `Fail`
- bandwidth and latency values are `Observation`
- component-level `Pass` is rejected while threshold mode is `observation`
- p99, p99.9, and maximum-latency anomalies are retained
- a future mature-band violation becomes `Regression` and requires `Review`

## 4. Analyzer Input Contract

The analyzer accepts one JSON evidence index. It validates the linked source
manifest and required artifacts before aggregating component verdicts. It
never invokes a workload.

```json
{
  "profile_id": "EXT-REGRESSION-COMPACT-001",
  "run_id": "external_ssd_regression_YYYYMMDD",
  "components": [
    {
      "component_id": "REG-PERF-RR-4K-QD1",
      "evidence_status": "complete",
      "performance_verdict": "Observation",
      "qos_verdict": "Observation",
      "source_manifest": "results/external_ssd/.../run_manifest.json"
    },
    {
      "component_id": "REG-DATA-CRC32C-4G",
      "evidence_status": "limited",
      "integrity_verdict": "Pass",
      "host_observer_status": "limited",
      "source_manifest": "results/external_ssd/.../run_manifest.json"
    }
  ]
}
```

Contract rules:

- `run_id` is required and nonempty
- each received YAML component ID appears at most once
- unknown or duplicate component IDs are rejected
- every received component links an existing repository-relative
  `run_manifest.json`; absolute paths and repository escapes are rejected
- source `test_case_id`, status, matching fio job options, repeat count, and
  YAML `required_evidence` artifacts are verified
- summary evidence must contain condition-matching rows and complete p99/p99.9
  fields when those metrics are required
- errored fio jobs cannot support a successful evidence or integrity claim
- evidence-index status cannot be stronger than the source-manifest status
- integrity and host-observer verdicts must match the linked analysis manifest
- absent components become `Blocked`
- performance components provide performance and QoS verdicts
- the integrity component provides integrity and host-observer verdicts
- `host_observer_gating: false` keeps observer limitations separate from the
  integrity verdict; a future gating component blocks unless observer evidence
  is complete

## 5. Analyzer Outputs

```text
regression_component_summary.csv
regression_verdict.json
```

The aggregate JSON preserves:

- `evidence_status`
- `integrity_verdict`
- `performance_verdict`
- `qos_verdict`
- `host_observer_status`
- `release_verdict`

Release precedence is:

```text
integrity Fail
-> missing/blocked critical evidence
-> performance or QoS Regression requiring Review
-> Observation while thresholds are immature
-> Pass after mature thresholds are defined
```

`host_observer_status: limited` propagates to evidence status but does not
overwrite `integrity_verdict: Pass`. This preserves the distinction between
correctness evidence and diagnostic coverage.

## 6. Invocation Contract

The following command analyzes an already prepared evidence index only:

```powershell
python .\scripts\analysis\analyze_external_ssd_regression.py `
  --evidence-index .\path\to\evidence_index.json `
  --output-dir .\path\to\analysis
```

There is intentionally no regression runner in this design commit.

## 7. Safety and Interpretation Boundary

- file targets only; never a raw physical drive
- no workload is launched by the analyzer
- no automatic deletion of the integrity target
- Windows/USB/exFAT effects remain part of the measured path
- observer limitations remain explicit
- no internal FTL/GC cause is inferred
