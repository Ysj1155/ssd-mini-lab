# SSD Mini Lab

Black-box SSD validation mini-lab using fio, Python, and PowerShell.

This repository treats a real SSD as a DUT (Device Under Test) and builds portfolio evidence around product-style validation: test condition design, controlled fio execution, JSON-to-CSV parsing, repeatability review, p99/p99.9 latency analysis, sustained workload observation, and clear interpretation limits.

This is intentionally separate from my FTL/GC white-box study project. This repo focuses on what can be observed from the outside of a real storage device.

## Portfolio Snapshot

| Validation question | Evidence |
|---|---|
| How does queue depth affect throughput and tail latency? | `results/qd_sweep_grouped.csv`, `docs/reports/reproducibility_qd_sweep.md` |
| How much do repeated runs vary? | `results/qd_sweep_reproducibility.csv` |
| How does direct I/O differ from buffered I/O? | `docs/reports/direct_buffered_week7.md`, `results/direct_buffered_comparison.csv` |
| Does path/runtime context change fio behavior? | `docs/reports/wsl_path_compare_week9.md`, `docs/reports/sustained_workload_week10.md` |
| Can an external SSD be handled as a black-box DUT? | `docs/reports/external_ssd_product_validation.md` |

## Current Highlight: External SSD DUT Validation

The current product-validation track uses an external SanDisk SSD through a file target under `E:\validation`.

Core artifacts:

| Artifact | Path |
|---|---|
| DUT profile | `docs/reports/external_ssd_dut_profile.md` |
| Requirement matrix | `docs/reports/external_ssd_requirement_matrix.md` |
| Execution runbook | `docs/reports/external_ssd_execution_runbook.md` |
| Product validation report | `docs/reports/external_ssd_product_validation.md` |
| Test matrix | `configs/external_ssd_validation_matrix.yaml` |
| Raw fio JSON/logs | `results/external_ssd/` |
| Parsed CSV summaries | `results/external_ssd_*.csv` |

Latest completed external SSD result:

| Workload | Runtime | QD | Repeats | Avg BW MiB/s | Avg IOPS | Avg p99 us | Avg p99.9 us |
|---|---:|---:|---:|---:|---:|---:|---:|
| randwrite 4k | 120s | 16 | 3 | 162.96 | 41,716.65 | 516.10 | 735.91 |

Interpretation boundary: these are black-box file-target results through USB, Windows, and exFAT. They are useful for validation workflow evidence, but they do not prove internal SSD FTL or GC behavior.

## Repository Layout

```text
ssd-mini-lab/
  README.md
  configs/                 # validation matrices
  docs/
    reports/               # portfolio reports and experiment writeups
    notes/                 # working notes
  fio/                     # small baseline fio JSON samples
  results/                 # documented raw results, summaries, and plots
  scripts/
    analysis/              # Python parsers/analyzers/plot builders
    runners/               # PowerShell fio runners
```

Large local fio test files are ignored by Git. Documented raw JSON/CSV/plot outputs are kept when they support an experiment report.

## Runbook Entry Points

Use PowerShell from the repository root unless a report says otherwise.

Baseline parsing:

```powershell
cd D:\ssd_lab
python .\scripts\analysis\parse_fio_results.py
```

Queue-depth analysis:

```powershell
cd D:\ssd_lab
python .\scripts\analysis\analyze_qd_sweep.py
python .\scripts\analysis\analyze_qd_reproducibility.py
```

External SSD QD sweep:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_EXTERNAL_TESTFILE = "E:\validation\ssd_lab_fio_testfile"
powershell -ExecutionPolicy Bypass -File .\scripts\runners\run_external_ssd_qd_smoke.ps1
```

External SSD sustained run:

```powershell
cd D:\ssd_lab
$env:SSD_LAB_EXTERNAL_TESTFILE = "E:\validation\ssd_lab_fio_testfile"
$env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL = "sustained_rand_write_120s_qd16_repeat3"
$env:SSD_LAB_EXTERNAL_SUSTAINED_WORKLOAD = "rand_write"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RW = "randwrite"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNTIME = "120"
$env:SSD_LAB_EXTERNAL_SUSTAINED_SIZE = "512M"
$env:SSD_LAB_EXTERNAL_SUSTAINED_IODEPTH = "16"
$env:SSD_LAB_EXTERNAL_SUSTAINED_RUNS = "3"
powershell -ExecutionPolicy Bypass -File .\scripts\runners\run_external_ssd_sustained.ps1
```

## Main Reports

| Report | Purpose |
|---|---|
| `docs/reports/portfolio_evidence.md` | Evidence map for portfolio review |
| `docs/reports/ssd_validation_competency_map.md` | Mapping to SSD Validation Engineer competencies |
| `docs/reports/korean_interview_brief.md` | Korean interview talking points |
| `docs/reports/validation_run_checklist.md` | Reusable pre-run/post-run checklist |
| `docs/reports/external_ssd_product_validation.md` | Current external SSD DUT validation report |
| `docs/reports/stage2_next_experiment_plan.md` | Next experiment plan |

## Tooling

- fio
- Python
- pandas
- matplotlib
- PowerShell
- Git / GitHub

## Project Direction

Future work should stay on the black-box validation side:

- define DUT profile and test requirements
- run controlled fio workloads
- preserve raw JSON/log evidence
- parse results into comparable CSVs
- review p99/p99.9 latency and repeatability
- document limitations before making claims

The goal is not to chase the highest benchmark number. The goal is to show a repeatable validation workflow: condition -> execution -> result -> interpretation.