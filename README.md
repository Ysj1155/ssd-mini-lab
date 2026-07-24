# SSD Mini Lab

Black-box SSD validation mini-lab using fio, Python, and PowerShell.

This repository treats a real SSD as a DUT (Device Under Test) and preserves a traceable validation flow:

```text
requirement -> condition -> runner / observer -> raw evidence -> analysis -> verdict
```

The goal is not to chase the highest benchmark number. The goal is to show controlled execution, reproducible evidence, tail-latency review, and honest interpretation limits.

This project is intentionally separate from the FTL/GC white-box study project. This repository measures externally observable device behavior; it does not claim internal NAND, FTL, or GC root cause.

## Current Track: External SSD DUT

The active track uses a SanDisk external SSD and a file target at `E:\validation\ssd_lab_fio_testfile`.

Interpretation boundary: results include the USB path, Windows, exFAT, and fio file-target effects.

| Validation question | Current evidence |
|---|---|
| How does QD affect 4K random performance and tail latency? | QD 1/4/16/32, read/write, 30s, repeat=3 |
| Are results repeatable? | Per-condition mean, standard deviation, and CV |
| Does sustained behavior differ from the short sweep? | Read/write QD16/QD32, 120s, repeat=3 |
| Does longer runtime expose write-side QoS risk? | Random write QD32, 120s vs 300s, repeat=3 |
| Can every result be traced to its conditions and evidence? | Run manifest plus separate runner/observer manifests |

Latest finding: three separately initiated paired sessions produced QD16 post-write bandwidth deltas of -6.37%, -7.59%, and +23.33%. The conditioning-uplift direction was mixed and therefore not reproduced under the controlled external sequence.

All three sessions preserve reconnect and same-port confirmations, complete parent/child manifests, matching pre-observer/runner/post-observer evidence, and paired comparison CSVs. The requirement passed because the evidence plan completed; the performance hypothesis did not.

The prepared next experiment, `EXT-LARGE-WS-SEQ-001`, addresses the 512 MiB working-set limit with one completion-based 32 GiB sequential write and read against a dedicated E: file. Any throughput transition remains an external observation rather than proof of cache, FTL, or GC behavior.

## Start Here

| Purpose | Path |
|---|---|
| DUT definition | `docs/reports/external_ssd_dut_profile.md` |
| Requirements and verdict rules | `docs/reports/external_ssd_requirement_matrix.md` |
| Next execution procedure | `docs/reports/external_ssd_execution_runbook.md` |
| Current result interpretation | `docs/reports/external_ssd_product_validation.md` |
| Machine-readable test matrix | `configs/external_ssd_validation_matrix.yaml` |
| Raw fio JSON and logs | `results/external_ssd/` |
| Parsed sustained CSVs | `results/external_ssd_sustained_*.csv` |

## Evidence Model

- Runner: executes fio and writes raw JSON/logs plus `runner_manifest.json`.
- Observer: collects read-only environment and telemetry evidence before and after fio.
- Analyzer: converts fio JSON/logs into comparable CSV summaries.
- Integrated manifest: links the DUT, requirements, conditions, artifacts, and evidence gaps under one `run_id`.
- Report: records observations, verdicts, anomalies, and interpretation boundaries.

Missing telemetry or execution evidence is recorded as `limited`; it is not silently treated as complete.

## Repository Layout

```text
ssd-mini-lab/
  configs/                 # machine-readable validation conditions
  docs/reports/            # runbook, requirements, and result reports
  fio/                     # small baseline fio samples
  results/                 # raw evidence and derived CSVs
  scripts/analysis/        # parsers, analyzers, manifest builder
  scripts/observers/       # read-only environment/telemetry collection
  scripts/runners/         # fio execution
  tests/                   # parser compatibility fixtures and tests
```

Large local fio test files are ignored by Git. Raw JSON/logs and derived CSVs are retained when they support a documented validation result.

## Verification

```powershell
cd D:\ssd_lab
python -m unittest discover -s tests -p "test_*.py"
python .\scripts\analysis\analyze_external_ssd_sustained.py
python .\scripts\analysis\build_external_ssd_run_manifest.py --all
```

Codex does not run fio for the external SSD track unless explicitly asked. The user confirms the target path and runs fio locally.
