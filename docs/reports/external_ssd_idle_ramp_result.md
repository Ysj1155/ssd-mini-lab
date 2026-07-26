# EXT-IDLE-RAMP-001 Result

Status: complete.

## 1. Decision

```text
requirement_verdict: Pass
performance_verdict: no_clear_idle_duration_association
```

The planned six phases completed, but the prior 37-53 second phase-start ramp
did not reproduce at any requested idle duration. Pre-probe idle length was
not a stable explanation for ramp presence, transition time, or overall
performance state in this session.

## 2. Validation Question

The second independent mixed-ratio session had shown a phase-start bandwidth
ramp in eight of nine phases. `EXT-IDLE-RAMP-001` isolated requested
pre-probe idle duration while holding the following controls fixed:

- existing 32 GiB file target on the same external SSD and physical USB port
- 4K `randrw`, 70% read / 30% write
- QD16, `direct=1`, `windowsaio`, `numjobs=1`
- 120 seconds per phase and `randrepeat=1`

The mirrored sequence was:

```text
300s -> 60s -> 0s -> 0s -> 60s -> 300s
 A1      B1    C1   C2    B2      A2
```

Each idle condition appeared once in the early half and once in the late half.

## 3. Evidence Completeness

- experiment and runner status: `complete`
- fio phase count: 6
- fio error count: 0
- one-second fio log count: 30
- observed read share: 69.98-70.00%
- actual controlled idle sequence: approximately
  300.04 / 60.02 / 0 / 0 / 60.01 / 300.01 seconds
- pre/post observer evidence: present, telemetry status `limited`
- integrated run manifest: `complete`, zero anomalies

The observer limitation was unchanged: SMART was unavailable, storage
reliability counters were inaccessible through the current Windows path, and
the fsutil disk-free query returned a nonzero exit code.

## 4. Phase Results

| Phase | Idle | Transition | Ramp | Total BW MiB/s | Read p99 ms | Read p99.9 ms |
|---|---:|---:|---|---:|---:|---:|
| A1 | 300 s | 1.002 s | No | 127.528 | 0.782 | 2.933 |
| B1 | 60 s | 20.016 s | No | 174.643 | 0.602 | 0.864 |
| C1 | 0 s | 2.002 s | No | 158.898 | 0.717 | 2.179 |
| C2 | 0 s | 1.001 s | No | 182.518 | 0.635 | 1.237 |
| B2 | 60 s | 1.002 s | No | 173.947 | 0.635 | 1.090 |
| A2 | 300 s | 1.002 s | No | 198.733 | 0.602 | 1.188 |

Transition time is the first timestamp at which total bandwidth remains at or
above 80% of the last-third mean for five consecutive one-second samples. A
ramp additionally requires a transition of at least 10 seconds and a
last-third/first-third bandwidth ratio of at least 1.30.

B1 reached the threshold at 20.016 seconds, but its last/first ratio was only
1.170. C2 had a last/first ratio of 1.305, but it reached the transition
threshold at 1.001 seconds. Neither satisfied both ramp criteria.

## 5. Idle-Pair Comparison

| Requested idle | Ramp count | Pair classification | BW repeat 1 | BW repeat 2 | Repeat 2 / 1 |
|---:|---:|---|---:|---:|---:|
| 0 s | 0 / 2 | Consistent: no ramp | 158.898 | 182.518 | 1.149x |
| 60 s | 0 / 2 | Consistent: no ramp | 174.643 | 173.947 | 0.996x |
| 300 s | 0 / 2 | Consistent: no ramp | 127.528 | 198.733 | 1.558x |

All three mirrored pairs agreed on ramp absence. This is classification
consistency, not full performance reproducibility. The 300-second pair differed
by 55.8%, and the 0-second pair differed by 14.9%. Only the 60-second pair had
similar average bandwidth.

Mean bandwidth by idle condition was not monotonic:

- 0 seconds: 170.708 MiB/s
- 60 seconds: 174.295 MiB/s
- 300 seconds: 163.131 MiB/s

Read p99 and p99.9 also did not establish a stable monotonic idle-duration
response.

## 6. Time-Window Review

The phase shapes differed, but not in a way that tracked idle duration:

- A1 fell during the first minute and recovered after 60 seconds.
- B1 rose gradually, without reaching the defined 30% ramp magnitude.
- C2 began high, dipped during 10-30 seconds, and recovered later.
- B2 and A2 declined in the final 30-second window.

The earlier session-wide 37-53 second ramp pattern was therefore absent.
Individual rises and falls remained, but their timing and direction did not
follow the requested idle sequence.

## 7. Conclusion

`REQ-IDLE-RAMP-007` passes because all planned phases, mirrored pairs,
transition metrics, QoS metrics, observer evidence, and traceability artifacts
exist.

The performance hypothesis is not supported:

> Under this fixed 70:30, 4K, QD16 sequence, requested pre-probe idle duration
> did not reproduce the prior phase-start ramp or explain transition time.

The broader black-box observation remains that throughput state can change
substantially across phases even when the visible workload controls are held
constant. This result does not identify USB power state, host activity,
filesystem behavior, thermal state, firmware, cache, FTL, GC, or NAND as the
cause.

## 8. Evidence

- `results/external_ssd/sustained_idle_ramp_7030_32g_20260725/run_manifest.json`
- `results/external_ssd/sustained_idle_ramp_7030_32g_20260725/analysis/phase_summary.csv`
- `results/external_ssd/sustained_idle_ramp_7030_32g_20260725/analysis/window_summary.csv`
- `results/external_ssd/sustained_idle_ramp_7030_32g_20260725/analysis/transition_summary.csv`
- `results/external_ssd/sustained_idle_ramp_7030_32g_20260725/analysis/idle_condition_summary.csv`
- `results/external_ssd/sustained_idle_ramp_7030_32g_20260725/analysis/verdict.csv`
- `results/external_ssd/sustained_idle_ramp_7030_32g_20260725/analysis/analysis_manifest.json`
