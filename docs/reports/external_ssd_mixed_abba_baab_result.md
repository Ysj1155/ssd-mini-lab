# External SSD Mixed Read-QoS ABBA/BAAB Result

## Verdict

Performance hypothesis:

> Adding 30% random writes produces repeatable read p99/p99.9 inflation under matched 4K QD16 conditions.

Verdict: `not_reproduced_under_controlled_abba_baab_sequences`

The evidence requirements passed because both planned sequences completed with
traceable raw data. The performance hypothesis did not pass because the mixed
phases did not preserve a consistent direction across sequence position or
independent reconnect-start sessions.

## Controlled Conditions

Both sessions used the same dedicated 32 GiB file target, 4K blocks, QD16,
180-second time-based phases, direct I/O, one job, `windowsaio`, and
`randrepeat=1`.

```text
ABBA: A1 pure read -> B1 70:30 -> B2 70:30 -> A2 pure read
BAAB: B1 70:30 -> A1 pure read -> A2 pure read -> B2 70:30
```

BAAB began after a user-confirmed 10-minute disconnect, same-port reconnect,
and runner-controlled 5-minute idle. Reconnect-start is an external condition,
not proof of an internally reset SSD state.

## Per-Phase Read Results

| Session | Phase | Workload | BW MiB/s | p99 ms | p99.9 ms | Max ms |
|---|---|---|---:|---:|---:|---:|
| ABBA | A1 | pure read | 157.649 | 0.668 | 1.958 | 125.307 |
| ABBA | B1 | mixed 70:30 | 124.039 | 0.594 | 0.864 | 9.159 |
| ABBA | B2 | mixed 70:30 | 88.331 | 0.799 | 3.391 | 141.418 |
| ABBA | A2 | pure read | 141.283 | 0.586 | 1.745 | 59.442 |
| BAAB | B1 | mixed 70:30 | 112.800 | 0.635 | 1.204 | 29.211 |
| BAAB | A1 | pure read | 189.538 | 0.561 | 0.881 | 45.133 |
| BAAB | A2 | pure read | 208.758 | 0.553 | 0.823 | 83.769 |
| BAAB | B2 | mixed 70:30 | 138.052 | 0.578 | 0.872 | 102.151 |

## Reproduction Check

| Comparison | Read BW | Read p99 | Read p99.9 |
|---|---:|---:|---:|
| ABBA A2/A1 | 0.896x | 0.877x | 0.891x |
| ABBA B2/B1 | 0.712x | 1.345x | 3.925x |
| BAAB A2/A1 | 1.101x | 0.986x | 0.934x |
| BAAB B2/B1 | 1.224x | 0.910x | 0.724x |

ABBA B2 was slower and had worse tail latency than B1. BAAB reversed that
direction: B2 was faster and had lower p99 and p99.9 than B1. The second mixed
phase therefore does not have a stable degradation direction.

The mean mixed/pure-read p99 and p99.9 ratios were modestly above 1.0 in both
sessions, but individual mixed phases varied too widely to establish a
repeatable causal effect. Maximum-latency spikes also did not move with p99 and
p99.9 consistently, so isolated maxima remain separate black-box anomalies.

## Decision

- Close the original mixed read-tail hypothesis as `not reproduced`.
- Do not claim that write mixing, elapsed time, USB, cache, FTL, GC, NAND, or
  firmware caused the observed phase differences.
- Continue with `EXT-MIXED-RATIO-SWEEP-001` only as descriptive response
  mapping, not as causal confirmation.
- Preserve ratio, cycle, and sequence position together in every comparison.

## Evidence

- `results/external_ssd/_experiments/mixed_read_qos_abba_32g_20260724/experiment_manifest.json`
- `results/external_ssd/sustained_mixed_read_qos_abba_32g_20260724/`
- `results/external_ssd/_experiments/mixed_read_qos_baab_32g_20260724/experiment_manifest.json`
- `results/external_ssd/sustained_mixed_read_qos_baab_32g_20260724/`
- `docs/reports/external_ssd_mixed_abba_runbook.md`
- `docs/reports/external_ssd_mixed_baab_runbook.md`

Observer status is Limited because device reliability/SMART evidence was not
available through the current Windows path. This limitation does not invalidate
the fio result files, but it prevents device-internal root-cause attribution.
