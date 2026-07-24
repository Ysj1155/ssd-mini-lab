# External SSD Execution Runbook

Codex prepares and reviews external SSD workflows but does not run fio unless explicitly asked. The user confirms the physical setup and executes prepared PowerShell runners locally.

## 1. Completed State Study

`EXT-STATE-REPRO-002` completed on 2026-07-23 with three separately initiated sessions.

Each session preserved:

```text
10-minute user-confirmed disconnect
  -> reconnect to the same physical USB port
  -> 5-minute idle
  -> QD16 baseline, 120s, run=1
  -> QD32 conditioning, 300s, run=1
  -> 60-second idle
  -> QD16 post-write, 120s, run=1
```

| Session | Baseline MiB/s | Post MiB/s | BW delta | p99 delta | p99.9 delta |
|---:|---:|---:|---:|---:|---:|
| 1 | 123.85 | 115.96 | -6.37% | +27.62% | +66.19% |
| 2 | 140.87 | 130.17 | -7.59% | +27.34% | +108.97% |
| 3 | 110.34 | 136.08 | +23.33% | -46.24% | -75.00% |

Study verdict: `not_reproduced_under_controlled_external_sequence`.

`REQ-STATE-REPRO-002` is Pass because all planned sessions, raw evidence, paired metrics, and traceability artifacts exist. The conditioning-uplift hypothesis is not reproduced because the paired direction is mixed.

## 2. Evidence Regeneration

```powershell
cd D:\ssd_lab
python .\scripts\analysis\analyze_external_ssd_sustained.py
python .\scripts\analysis\analyze_external_ssd_state_repro.py
python .\scripts\analysis\build_external_ssd_run_manifest.py --all
```

Primary evidence:

- `results/external_ssd_state_repro_pairs.csv`
- `results/external_ssd_state_repro_study_summary.csv`
- `results/external_ssd/_experiments/state_repro_002_session*/experiment_manifest.json`
- child raw JSON/logs and integrated `run_manifest.json` files

## 3. Interpretation Boundary

- Reconnect-start is an externally controlled label, not proof of an internally reset SSD state.
- USB, Windows, exFAT, file-target, and device behavior remain combined.
- SMART, reliability counters, and direct power measurement remain Limited.
- The 512 MiB file target does not establish large-working-set or full-drive behavior.

## 4. Next Execution Status

The state study is closed. Do not add more sessions merely to search for a preferred direction.

The next experiment should address the working-set and sequential-workload coverage gap. Its exact safety checks and execution command must be fixed before fio is run.
