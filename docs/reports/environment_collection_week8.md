# Week 8 - Environment Collection

## Purpose

Week 8 starts Stage 2 by collecting environment information before adding more benchmark workloads.

The goal is to make future SSD mini-lab results easier to reproduce and interpret. Performance numbers are only meaningful when the test environment is known.

## Why This Matters

SSD validation results can be affected by many layers:

- host OS
- filesystem
- Python and analysis package versions
- fio version
- Git commit state
- disk/volume path
- WSL availability
- USB enclosure or bridge path
- permission level of the user running the test

Stage 1 already showed that the I/O path matters. The direct/buffered experiment reported better `direct=0` results, but those results likely include OS cache and filesystem effects. Stage 2 therefore begins by recording environment state explicitly.

## New Script

```text
scripts/collect_env_windows.ps1
```

Run:

```powershell
cd D:\ssd_lab
powershell -ExecutionPolicy Bypass -File .\scripts\collect_env_windows.ps1
```

Output:

```text
results/env/<timestamp>/
results/env/latest/
```

`results/env/` is ignored by Git because the files are machine-specific and change on every run.

Stage 2 also adds a storage telemetry collector:

```text
scripts/collect_storage_telemetry_windows.ps1
```

Run:

```powershell
cd D:\ssd_lab
powershell -ExecutionPolicy Bypass -File .\scripts\collect_storage_telemetry_windows.ps1
```

Output:

```text
results/telemetry/<timestamp>/
results/telemetry/latest/
```

`results/telemetry/` is ignored by Git for the same reason as `results/env/`.

## Collected Files

| File | Purpose |
|---|---|
| `manifest.json` | Collection timestamp and output path |
| `powershell_version.txt` | PowerShell runtime information |
| `windows_computer_info.txt` | Windows host information |
| `cpu_memory.txt` | CPU and memory information where accessible |
| `disk_info.csv` | Disk information where accessible |
| `volume_info.csv` | Volume information where accessible |
| `logical_disk_info.csv` | Logical disk information where accessible |
| `psdrive_filesystem_info.csv` | Lower-permission filesystem drive fallback |
| `fio_version.txt` | fio version |
| `python_version.txt` | Python version |
| `pip_freeze.txt` | Python package versions |
| `git_version.txt` | Git version |
| `git_state.txt` | Repository root, commit hash, and working tree status |
| `wsl_status.txt` | WSL status |
| `wsl_list.txt` | Installed WSL distributions, if any |
| `wsl_linux_env.txt` | Linux-side environment output, if a WSL distro is available |
| `wsl_tool_versions.txt` | fio, Python, Git, and sysstat tool versions inside WSL |

## Storage Telemetry Files

| File | Purpose |
|---|---|
| `manifest.json` | Collection timestamp, output path, and read-only safety note |
| `disk_info.csv` | Windows disk metadata, if permission allows |
| `physical_disk.csv` | Physical disk metadata, if permission allows |
| `storage_reliability_counters.csv` | Read-only reliability counters, if permission allows |
| `volume_info.csv` | Volume metadata, if permission allows |
| `partition_info.csv` | Partition metadata, if permission allows |
| `logical_disk_info.csv` | Logical disk metadata, if permission allows |
| `win32_diskdrive.csv` | Win32 disk-drive fallback metadata, if permission allows |
| `driveinfo_D.txt` | Low-permission .NET DriveInfo fallback for D: |
| `fsutil_volume_diskfree_D.txt` | fsutil D: free-space output, if permission allows |
| `testfile_info.txt` | Current sustained fio test-file path and size |
| `smartctl_availability.txt` | Whether `smartctl` is available |
| `smartctl_scan.txt` | Optional smartctl scan note or output |

## Current Run Notes

The script was tested on May 30, 2026.

Observed from the Windows-side collection:

- fio was available: `fio-3.42`
- Python was available: `Python 3.12.1`
- Git state was captured successfully after normalizing the safe-directory path.
- Some disk/volume queries failed with permission errors from the sandbox account.

The permission failures are useful information rather than a script failure. They show that environment collection depends on the account and privilege level used to run the test. Running the script from the normal user PowerShell may collect more disk and volume details.

Observed from the WSL-side collection after Ubuntu setup:

- WSL distro: `Ubuntu`
- Ubuntu version: `Ubuntu 24.04.1 LTS (Noble Numbat)`
- Kernel: `6.6.114.1-microsoft-standard-WSL2`
- WSL root filesystem: `/dev/sdd`, mounted at `/`
- Windows `C:\` mounted at `/mnt/c`
- Windows `D:\` mounted at `/mnt/d`
- `D:\` had about 1.4 TiB available in the sample run.

This means future experiments can distinguish at least two safe file-based paths:

| Path type | Example | Meaning |
|---|---|---|
| WSL native ext4 path | `/home/<user>/ssd_lab/...` | Stored inside the WSL virtual disk |
| Windows-mounted path | `/mnt/d/ssd_lab/...` | Goes through the Windows drive mount path |

Neither path should be treated as raw block-device validation. Both are still safe file-based tests.

Observed from the storage telemetry recon on June 8, 2026:

- The collector ran successfully and wrote `results/telemetry/latest/`.
- `.NET DriveInfo` reported `D:\` as a fixed NTFS drive with about 1.41 TB available.
- The sustained fio test file existed at `D:\ssd_lab\fio_testfile_sustained_smoke` and was 1 GiB at the time of collection.
- `Get-Disk`, `Get-PhysicalDisk`, `Get-StorageReliabilityCounter`, `Get-Volume`, and related disk queries were blocked by access-denied errors under the Codex sandbox account.
- `smartctl` was not available in the current command environment, and the optional smartctl scan was not run.

This means the current telemetry recon proves the run path, free-space fallback, test-file state, and permission boundary. It does not yet provide device-level SMART/NVMe health evidence.

## Interpretation

This lab does not add a new performance benchmark. It adds a reproducibility layer.

Before comparing future Windows, WSL, or sustained workload results, each run should have an environment snapshot. That makes it easier to answer:

- Which fio version produced this result?
- Which Python environment generated the CSV and plots?
- Which Git commit was used?
- Was WSL actually available?
- Did the script have enough permission to inspect disk and volume metadata?
- Are results tied to a Windows file path, WSL mount path, or another storage path?

## Validation Lessons

1. Environment metadata is part of the test result.
2. Missing telemetry should be recorded, not silently ignored.
3. Permission level can affect what can be observed.
4. A repeatable benchmark needs a repeatable environment snapshot.
5. WSL availability should be confirmed before using it as a test path.
6. WSL native ext4 and `/mnt/d` are different paths and should not be mixed without labeling.

## Limitations

- The script is Windows-first.
- SMART/NVMe telemetry is only available if the host has suitable tools and permissions.
- It does not run fio.
- Some disk and volume commands may require permissions not available in restricted environments.
- WSL output requires the configured distro name to exist. The default is `Ubuntu`.

To use a different WSL distro name:

```powershell
$env:SSD_LAB_WSL_DISTRO = "Ubuntu-24.04"
powershell -ExecutionPolicy Bypass -File .\scripts\collect_env_windows.ps1
```

## Next Step

The next lab can safely compare file-path behavior only after the environment snapshot is captured:

1. Run `collect_env_windows.ps1`.
2. Confirm WSL has a usable Ubuntu distribution.
3. Confirm fio is installed inside Ubuntu.
4. Compare WSL native ext4 path vs `/mnt/d` with small file-based fio tests.
5. Keep the test file size small and avoid raw device targets.
