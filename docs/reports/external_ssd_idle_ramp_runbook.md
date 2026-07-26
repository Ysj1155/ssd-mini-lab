# EXT-IDLE-RAMP-001 Runbook

Status: completed on 2026-07-25. See `external_ssd_idle_ramp_result.md`.

## 1. Validation Question

The second independent mixed-ratio session showed a phase-start bandwidth
ramp in eight of nine phases. Its automated transition time was approximately
37-53 seconds, while the first session usually reached its plateau
immediately.

`EXT-IDLE-RAMP-001` asks one narrower question:

> With workload, target, queue depth, runtime, random sequence, and USB port
> held fixed, is the presence or timing of the phase-start ramp associated
> with the intentional idle interval immediately before fio?

This is an external black-box association test. It cannot identify USB power
state, Windows behavior, filesystem activity, firmware, cache, FTL, GC, NAND,
or thermal state as the cause.

## 2. Experimental Design

The only intentionally changed variable is pre-probe idle duration.

| Field | Fixed value |
|---|---|
| Target | `E:\validation\ssd_lab_seq_32g` |
| Workload | 4K `randrw`, 70% read / 30% write |
| Queue depth | 16 |
| Working set | 32 GiB existing dedicated file |
| Runtime | 120 seconds per phase |
| I/O mode | `direct=1`, `windowsaio`, `numjobs=1` |
| Random sequence | `randrepeat=1` |
| Physical path | Same external SSD and same USB port |

The six-phase sequence is mirrored:

| Phase | Code | Requested idle | Repeat |
|---:|---|---:|---:|
| 1 | A1 | 300 s | 1 |
| 2 | B1 | 60 s | 1 |
| 3 | C1 | 0 s | 1 |
| 4 | C2 | 0 s | 2 |
| 5 | B2 | 60 s | 2 |
| 6 | A2 | 300 s | 2 |

`A-B-C-C-B-A` places every idle condition once in the early half and once in
the late half. Agreement within each mirrored pair makes a simple elapsed-time
or phase-order explanation less likely. A requested 0-second idle means no
intentional `Start-Sleep`; manifest timestamps preserve the actual runner gap.

The sequence adds six 120-second probes, or 720 seconds of workload. This is
less than half the fio duration of one nine-phase, 180-second ratio sweep and
does not add another broad workload matrix.

## 3. Metrics and Verdict Rules

Primary transition metric:

```text
first timestamp at which total bandwidth remains at or above
80% of the last-third mean for five consecutive 1-second samples
```

A phase is classified as `ramp_present` only when:

```text
transition_sec >= 10
and
last-third mean BW / first-third mean BW >= 1.30
```

Each idle pair is consistent when both repeats agree on ramp presence and,
when both contain a ramp, their transition times differ by no more than
20 seconds.

The analyzer reports `idle_duration_association_observed` only when all three
mirrored pairs are consistent and ramp frequency or transition time increases
with idle duration. Otherwise it reports
`no_clear_idle_duration_association`.

## 4. Preflight

1. Safely disconnect the external SSD for at least 10 minutes.
2. Reconnect it to the same physical USB port used for the prior sessions.
3. Close applications that may access E: and avoid foreground disk activity.
4. Open PowerShell and verify the dedicated file and volume.

```powershell
cd D:\ssd_lab

Get-Item E:\validation\ssd_lab_seq_32g |
  Select-Object FullName, Length, LastWriteTime

Get-Volume -DriveLetter E
```

The file must already exist and be exactly 32 GiB. The runner never targets a
raw physical drive.

## 5. Execute

Codex does not run this fio command. Run it locally after the preflight:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\runners\run_external_ssd_idle_ramp.ps1 `
  -ExperimentLabel "idle_ramp_7030_32g_20260725" `
  -TestFile "E:\validation\ssd_lab_seq_32g" `
  -ConfirmedDisconnectMinutes 10 `
  -RuntimeSec 120 `
  -ConfirmReconnectStart `
  -ConfirmSamePort `
  -ConfirmDedicatedFileWrite
```

Expected duration after starting the runner is about 25 minutes: 12 minutes
of fio, 12 minutes of intentional idle, plus observer and runner overhead.

Do not use the computer for unrelated storage work until the runner completes.

## 6. Analyze

After all six phases complete:

```powershell
python .\scripts\analysis\analyze_external_ssd_idle_ramp.py `
  --experiment-label idle_ramp_7030_32g_20260725
```

Expected analysis artifacts:

- `phase_summary.csv`
- `window_summary.csv`
- `transition_summary.csv`
- `idle_condition_summary.csv`
- `verdict.csv`
- `analysis_manifest.json`

## 7. Completion Checks

```powershell
$label = "idle_ramp_7030_32g_20260725"
$result = ".\results\external_ssd\sustained_$label"
$experiment = ".\results\external_ssd\_experiments\$label"

Get-ChildItem "$result\*.json" |
  Select-Object Name, Length, LastWriteTime

Select-String -Path "$result\*_phase*_idle*.json" `
  -Pattern '"error"|"filename"'

Get-Content -Raw "$experiment\experiment_manifest.json"
Import-Csv "$result\analysis\idle_condition_summary.csv" | Format-Table
Import-Csv "$result\analysis\verdict.csv" | Format-List
```

Valid evidence requires six complete fio JSON files with `error: 0`, both
read and write I/O near the requested 70:30 byte mix, six timestamped phase
records, pre/post observer evidence, and generated analysis artifacts.

## 8. Interpretation

- If 0-second phases have no ramp while 60/300-second pairs repeatedly show
  later transitions, the result supports an external idle-duration
  association.
- If all three idle conditions show similar ramps and transition times, the
  prior 37-53 second behavior is not explained by idle length.
- If mirrored repeats disagree, session or time-varying state remains stronger
  than a stable idle-duration effect.

Even a positive association is not proof of a wake-up mechanism, USB cause,
thermal behavior, cache state, or device-internal recovery process.
