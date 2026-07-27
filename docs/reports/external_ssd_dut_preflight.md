# External SSD DUT Read-Only Preflight

## Purpose

This check closes the gap between mocked safety-contract tests and the
physically attached external SSD. It validates the enrolled Windows volume,
disk identity, canonical file-target containment, health state, and an
existing target's size without launching fio or mutating the DUT.

## Invocation

Run PowerShell with execution-policy bypass because the checker imports the
shared safety module:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\observers\check_external_ssd_dut_preflight.ps1 `
  -TestFile E:\validation\ssd_lab_verify_4g_20260727_retry1 `
  -ExpectedFileBytes 4294967296
```

The checker is fail-closed. A path, identity, health, or size mismatch emits a
`Fail` JSON record and returns a nonzero exit code. It never enrolls a new
identity, invokes fio, creates a DUT file, changes file length, or deletes a
target.

## Actual DUT Verification

The attached E: device passed the read-only check on 2026-07-27. The preserved
machine-readable record is:

```text
results/external_ssd/dut_preflight_readonly_20260727/preflight.json
```

The evidence confirms:

- canonical target containment below `E:\validation`
- existing target size of exactly 4,294,967,296 bytes
- exFAT volume label and enrolled volume identity
- `SanDisk Extreme SSD` on the USB bus
- enrolled SHA-256 disk fingerprint match without storing the raw serial
- non-boot and non-system disk
- Windows volume health `Healthy` and operational status `OK`

This is safety evidence only. It does not re-verify file contents, measure
performance, or change the existing CRC32C integrity verdict.
