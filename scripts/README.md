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
- `analysis/analyze_external_ssd_sustained.py`
- `analysis/analyze_external_ssd_state_repro.py`
- `analysis/build_external_ssd_run_manifest.py`

Parser compatibility tests:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## `observers/`

Read-only evidence collectors that do not run fio.

- `observers/collect_external_ssd_observer.ps1`

## `runners/`

PowerShell wrappers for fio execution. Run them from the repository root unless the report says otherwise.

External SSD runners:

- `runners/run_external_ssd_qd_smoke.ps1`
- `runners/run_external_ssd_sustained.ps1`
- `runners/run_external_ssd_traced_sustained.ps1`
- `runners/run_external_ssd_state_recovery.ps1`
- `runners/run_external_ssd_state_repro_session.ps1`
- `runners/run_external_ssd_large_ws_seq.ps1`
- `runners/run_external_ssd_mixed_7030.ps1`
- `runners/run_external_ssd_mixed_controls.ps1`
- `runners/run_external_ssd_mixed_abba.ps1`

Safety note: external SSD runners require an explicit file target under `E:\validation` and do not use raw physical-drive targets.
