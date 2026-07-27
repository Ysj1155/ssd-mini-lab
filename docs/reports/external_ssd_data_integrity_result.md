# External SSD File-Target Integrity Result

Protocol: `EXT-DATA-INTEGRITY-001`

Evidence unit: `data_integrity_4g_20260727_retry1`

## 1. Question

Can one newly written 4 GiB file be read back completely with no fio CRC32C
verification error?

## 2. Controlled Conditions

| Item | Value |
|---|---|
| Target | `E:\validation\ssd_lab_verify_4g_20260727_retry1` |
| File size | 4 GiB |
| Block size | 1 MiB |
| Queue depth | 4 |
| Engine | `windowsaio` |
| Direct I/O | `1` |
| Verification | `crc32c` |
| fio version | `fio-3.42` |

The runner created a new exact-length file with `FileMode.CreateNew`, then fio
overwrote the complete file with CRC32C metadata and performed a separate
verify-only read.

## 3. Integrity Result

| Phase | fio error | Bytes | BW | p99 | p99.9 | Max |
|---|---:|---:|---:|---:|---:|---:|
| CRC32C write | 0 | 4,294,967,296 | 465.455 MiB/s | 10.289 ms | 11.076 ms | 239.891 ms |
| CRC32C verify read | 0 | 4,294,967,296 | 520.656 MiB/s | 7.832 ms | 15.401 ms | 17.386 ms |

The verify phase reported `verify=crc32c`, `verify_only=1`, `do_verify=1`, and
fio job error 0. fio 3.42 did not emit an explicit `verify_errors` field for
this successful run; the analyzer accepts its absence only when the verify
mode is present, the complete byte count matches, and the fio job error is
zero.

Integrity verdict:

```text
Pass
```

`REQ-DATA-009` passes.

## 4. Host Observation Result

Both synchronized observer processes ran without query errors:

| Phase | Samples | Nonzero activity samples | Effective status |
|---|---:|---:|---|
| CRC32C write | 16 | 0 | Limited |
| CRC32C verify read | 7 | 0 | Limited |

The Windows logical-disk provider returned only zero throughput, IOPS, queue,
and response-time values while fio reported active I/O. The files and manifests
exist, but they do not contain a usable workload signal.

Observer verdict:

```text
Limited
```

`REQ-HOST-OBS-010` is Limited. The collector and analyzer now require at least
one nonzero activity sample before synchronized evidence can be called
complete.

## 5. First-Attempt Finding

The original `data_integrity_4g_20260727` attempt wrote exactly 4 GiB with fio
error 0, but the file did not remain after fio created it. That failed evidence
was retained. The retry moved file creation into the runner using
`FileMode.CreateNew` and `SetLength`, matching the proven large-working-set
runner pattern. This kept the safety rule against pre-existing files while
allowing the verify-only phase to use the completed target.

## 6. Final Verdict

```text
integrity_verdict: Pass
evidence_status: Limited
integrated_run_status: Limited
```

The experiment proves one successful CRC32C file-target write/readback through
the tested Windows, exFAT, USB, bridge, and external-SSD path. It does not prove
power-loss protection, endurance, NAND/FTL behavior, internal ECC coverage, or
safe recovery after cable removal.

Primary evidence:

- `results/external_ssd/sustained_data_integrity_4g_20260727_retry1/integrity_summary.csv`
- `results/external_ssd/sustained_data_integrity_4g_20260727_retry1/integrity_verdict.csv`
- `results/external_ssd/sustained_data_integrity_4g_20260727_retry1/analysis_manifest.json`
- `results/external_ssd/sustained_data_integrity_4g_20260727_retry1/run_manifest.json`
