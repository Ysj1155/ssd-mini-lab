# Controlled Block-Size Sweep Result

Status: complete.

## 1. Decision

```text
requirement_verdict: Pass
performance_verdict: descriptive_block_size_mapping_complete
```

Both independent reconnect-start sessions completed. Under this QD32 random
file-target condition, 64K was the observed throughput knee: moving from 64K
to 1M produced no additional bandwidth while p99 latency increased by more
than 13x for read and 15x for write.

This is a condition-specific black-box observation, not a universal optimal
block size.

## 2. Validation Design

Fixed controls:

- target: `E:\validation\ssd_lab_seq_32g`
- existing dedicated file: 32 GiB
- workloads: independent `randread` and `randwrite` sessions
- queue depth: 32
- runtime: 30 seconds per phase
- I/O path: `direct=1`, `windowsaio`, `numjobs=1`
- repeats: three placements per block size and workload

Counterbalanced order:

| Cycle | Position 1 | Position 2 | Position 3 |
|---:|---|---|---|
| 1 | 4K | 64K | 1M |
| 2 | 64K | 1M | 4K |
| 3 | 1M | 4K | 64K |

Every block size appeared once in every cycle and sequence position.

## 3. Evidence Completeness

- read phase count: 9
- write phase count: 9
- fio error count: 0
- one-second fio log count: 45 per session
- direction validation: read session had zero write bytes; write session had
  zero read bytes
- session analyzers: complete
- paired analyzer: complete
- integrated run manifests: complete, zero anomalies
- pre/post observer manifests: present

Observer telemetry remained `limited` because SMART was unavailable, storage
reliability counters were inaccessible through the current Windows path, and
the fsutil disk-free query returned a nonzero exit code.

## 4. Block-Size Summary

| Workload | Block size | BW MiB/s | BW CV | IOPS | p99 ms | p99.9 ms | Maximum ms |
|---|---|---:|---:|---:|---:|---:|---:|
| Read | 4K | 215.511 | 2.24% | 55,170.8 | 0.870 | 1.374 | 23.189 |
| Read | 64K | 303.713 | 0.35% | 4,859.4 | 8.389 | 12.146 | 68.593 |
| Read | 1M | 304.145 | 0.03% | 304.1 | 115.518 | 181.404 | 221.975 |
| Write | 4K | 144.203 | 2.50% | 36,916.1 | 1.173 | 2.051 | 25.954 |
| Write | 64K | 497.109 | 0.15% | 7,953.7 | 4.446 | 5.669 | 46.386 |
| Write | 1M | 489.617 | 0.14% | 489.6 | 69.730 | 98.391 | 127.347 |

IOPS values are not directly comparable as a single performance score across
block sizes because every I/O transfers a different number of bytes.

## 5. Throughput Knee

Read:

- 64K / 4K bandwidth: 1.409x
- 1M / 64K bandwidth: 1.001x
- 1M / 64K p99 latency: 13.77x

Write:

- 64K / 4K bandwidth: 3.447x
- 1M / 64K bandwidth: 0.985x
- 1M / 64K p99 latency: 15.69x

The move from 4K to 64K increased throughput substantially. The move from 64K
to 1M did not improve throughput, but it increased completion latency sharply.
For this condition, 64K therefore provided the strongest observed
throughput/latency balance.

At fixed QD32, in-flight data also increases with block size:

- 4K: approximately 128 KiB
- 64K: approximately 2 MiB
- 1M: approximately 32 MiB

The latency increase is therefore part of the tested block-size/QD combination
and should not be interpreted as block size acting in isolation from
outstanding bytes.

## 6. Repeatability and Order Effects

Bandwidth repeatability was strong:

- read CV range: 0.03-2.24%
- write CV range: 0.14-2.50%

Aggregate cycle/position bandwidth movement was also small:

- read: approximately 1.2% range
- write: approximately 0.6% range

Block-size separation was much larger than the aggregate order effect. The
Latin-square design therefore supported a cleaner block-size interpretation
than a fixed 4K-to-1M sequence would have.

Tail latency was less uniform:

- read 64K Phase 9 reached p99.9 17.957 ms and maximum 68.593 ms
- write 64K Phase 9 reached p99.9 6.849 ms and maximum 46.386 ms
- write 4K p99.9 rose from 1.434 to 2.179 to 2.540 ms across its three
  placements

These remain QoS observations. Three placements are not sufficient to label
them deterministic late-session degradation.

## 7. Read/Write Comparison

| Block size | Write/read BW | Write/read p99 | Write/read p99.9 |
|---|---:|---:|---:|
| 4K | 0.669x | 1.349x | 1.493x |
| 64K | 1.637x | 0.530x | 0.467x |
| 1M | 1.610x | 0.604x | 0.542x |

Large-block write was faster than read in these two sessions. Because read and
write were independently initiated, this does not establish an intrinsic DUT
write-over-read advantage. It remains a descriptive result that includes the
USB path, host, filesystem, and session state.

## 8. Conclusion

`REQ-BS-008` passes because both workload sessions, 18 fio phases,
counterbalanced placements, repeat variation, QoS metrics, observer evidence,
paired comparison, and integrated traceability are complete.

The original controlled block-size roadmap item is closed:

> Under 4K/64K/1M random I/O at QD32, 64K reached the observed throughput
> plateau without the very large p99 cost of 1M. Sequence effects were small
> relative to block-size separation, while isolated tail-latency variation
> remained visible.

The evidence cannot identify USB, host scheduling, exFAT, firmware, cache,
thermal state, FTL, GC, or NAND as the cause of any observed behavior.

## 9. Evidence

- `results/external_ssd/sustained_block_size_randread_32g_20260726/run_manifest.json`
- `results/external_ssd/sustained_block_size_randread_32g_20260726/analysis/block_size_summary.csv`
- `results/external_ssd/sustained_block_size_randread_32g_20260726/analysis/cycle_position_summary.csv`
- `results/external_ssd/sustained_block_size_randwrite_32g_20260726/run_manifest.json`
- `results/external_ssd/sustained_block_size_randwrite_32g_20260726/analysis/block_size_summary.csv`
- `results/external_ssd/sustained_block_size_randwrite_32g_20260726/analysis/cross_workload_comparison.csv`
- `results/external_ssd/sustained_block_size_randwrite_32g_20260726/analysis/verdict.csv`
- `results/external_ssd/sustained_block_size_randwrite_32g_20260726/analysis/paired_analysis_manifest.json`
