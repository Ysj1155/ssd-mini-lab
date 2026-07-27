# External SSD File-Target Integrity Runbook

Protocol: `EXT-DATA-INTEGRITY-001`

Status: completed by `data_integrity_4g_20260727_retry1`; see `external_ssd_data_integrity_result.md`

## 1. Validation Question

Can one newly written 4 GiB file be read back completely with no fio CRC32C
verification error?

This is a data-path correctness check, not another performance sweep. The
primary output is an explicit integrity `Pass` or `Fail`. Bandwidth and latency
remain secondary execution context.

## 2. Safety Boundary

- Target only a new file under `E:\validation`.
- Never use `\\.\PhysicalDrive*`, a partition, or a volume as the fio target.
- The runner refuses an existing target and an existing result set.
- The runner does not delete the 4 GiB file after execution.
- The write confirmation applies only to the dedicated verification file.
- Keep at least 8 GiB free on E: before starting.

This protocol writes 4 GiB once and then reads/verifies 4 GiB once.

## 3. Fixed Conditions

| Item | Value |
|---|---|
| File size | 4 GiB |
| Write/read block size | 1 MiB |
| Queue depth | 4 |
| Engine | `windowsaio` |
| Direct I/O | `1` |
| Jobs | `1` |
| Verification | `crc32c` |
| Execution | completion based |
| Host observer | E: logical-disk counters every 1 second |

Phase 1 uses `verify=crc32c` and `do_verify=0` to write fio verification
metadata with the data. Phase 2 uses `verify_only=1`, `do_verify=1`, and
`readonly` to read and validate the existing file.

## 4. Preflight

Run PowerShell as Administrator, reconnect the SSD to the same physical USB
port used for the existing external-SSD evidence, and confirm:

```powershell
cd D:\ssd_lab

Get-Volume -DriveLetter E
Get-ChildItem E:\validation
Get-Command fio

Test-Path E:\validation\ssd_lab_verify_4g_20260727
```

The last command must return `False`. If it returns `True`, use a new
experiment label and a new target filename. Do not overwrite or delete it just
to make the command pass.

## 5. Execute

Codex does not run this fio workload. Run it locally:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_data_integrity.ps1 `
  -ExperimentLabel "data_integrity_4g_20260727" `
  -TestFile "E:\validation\ssd_lab_verify_4g_20260727" `
  -ObserverSampleIntervalMs 1000 `
  -ConfirmSamePort `
  -ConfirmDedicatedVerificationFileWrite
```

Expected sequence:

```text
runner creates a new, exact-length 4 GiB file with FileMode.CreateNew
-> pre environment/telemetry snapshot
-> synchronized host observer + complete 4 GiB CRC32C overwrite
-> synchronized host observer + complete verify-only read
-> post environment/telemetry snapshot
```

The runner stops immediately on a fio exit error, JSON job error, byte-count
mismatch, missing file, or unexpected file length.

## 6. Analyze

After both phases complete:

```powershell
python .\scripts\analysis\analyze_external_ssd_data_integrity.py `
  --experiment-id data_integrity_4g_20260727

python .\scripts\analysis\build_external_ssd_run_manifest.py `
  --result-set sustained_data_integrity_4g_20260727
```

Then inspect:

```powershell
Import-Csv `
  .\results\external_ssd\sustained_data_integrity_4g_20260727\integrity_verdict.csv

Get-ChildItem `
  .\results\external_ssd\sustained_data_integrity_4g_20260727\host_observer
```

## 7. Verdict Rule

Integrity is `Pass` only when:

- write job error is zero
- verify job error is zero
- both phases process exactly 4 GiB
- both jobs report `verify=crc32c`
- the verify phase reports verify-only or do-verify enabled
- any explicit verification-error counter is zero

Any nonzero fio or verification error, missing phase, or byte-count mismatch is
`Fail`.

Host-observer status is separate:

- `complete`: both phase counter manifests report Complete and each linked
  counter CSV contains at least one nonzero throughput-activity sample
- `limited`: a phase is missing, samples are absent or zero-only, counter
  access failed, or any sampling error was recorded

A `limited` observer does not turn a valid CRC32C result into an integrity
failure. It reduces diagnostic evidence coverage.

## 8. Interpretation Boundary

This result covers one Windows/USB/exFAT file-target write/readback path. It
does not prove:

- power-loss protection
- full-drive or long-term endurance
- NAND, FTL, garbage-collection, or firmware behavior
- internal ECC coverage
- integrity after unsafe cable removal

Retain the target until JSON, CSV, manifests, and verdict have been reviewed.
Any later cleanup is a separate, explicit user action.
