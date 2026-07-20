# Scripts

Repository scripts are grouped by purpose.

## `analysis/`

Python scripts for parsing fio JSON, building CSV summaries, and generating analysis artifacts.

Common entry points:

- `analysis/parse_fio_results.py`
- `analysis/analyze_qd_sweep.py`
- `analysis/analyze_qd_reproducibility.py`
- `analysis/analyze_qos_tail_latency.py`
- `analysis/analyze_sustained_smoke.py`

## `runners/`

PowerShell wrappers for fio execution. Run them from the repository root unless the report says otherwise.

External SSD runners:

- `runners/run_external_ssd_qd_smoke.ps1`
- `runners/run_external_ssd_sustained.ps1`

Safety note: external SSD runners require an explicit file target under `E:\validation` and do not use raw physical-drive targets.