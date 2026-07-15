# collect_storage_telemetry_windows.ps1
#
# Purpose:
#   Collect read-only storage telemetry for SSD mini-lab interpretation.
#
# Output:
#   results/telemetry/<timestamp>/
#
# Safety:
#   This script does not run fio.
#   This script does not write to raw block devices.
#   It only queries Windows storage metadata and read-only counters.

$ErrorActionPreference = "Continue"

$BaseDir = Split-Path -Parent $PSScriptRoot
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputRoot = Join-Path $BaseDir "results\telemetry"
$OutputDir = Join-Path $OutputRoot $Timestamp
$LatestDir = Join-Path $OutputRoot "latest"

New-Item -ItemType Directory -Force $OutputDir | Out-Null

function Write-Section {
    param(
        [string]$Path,
        [scriptblock]$Command
    )

    try {
        & $Command *>&1 | Out-File -FilePath $Path -Encoding utf8
    }
    catch {
        "ERROR: $($_.Exception.Message)" | Out-File -FilePath $Path -Encoding utf8
    }
}

function Export-SectionCsv {
    param(
        [string]$Path,
        [scriptblock]$Command
    )

    try {
        & $Command | Export-Csv -Path $Path -NoTypeInformation -Encoding utf8
    }
    catch {
        "ERROR: $($_.Exception.Message)" | Out-File -FilePath $Path -Encoding utf8
    }
}

function Write-Native {
    param(
        [string]$Path,
        [string]$Command,
        [string[]]$Arguments = @()
    )

    try {
        & $Command @Arguments *>&1 | Out-File -FilePath $Path -Encoding utf8
    }
    catch {
        "ERROR: $($_.Exception.Message)" | Out-File -FilePath $Path -Encoding utf8
    }
}

$manifest = [ordered]@{
    collected_at = (Get-Date).ToString("o")
    base_dir = $BaseDir
    output_dir = $OutputDir
    collector = "scripts/collect_storage_telemetry_windows.ps1"
    safety = "read-only metadata and telemetry queries; no fio; no raw-device writes"
}

$manifest | ConvertTo-Json -Depth 3 | Out-File -FilePath (Join-Path $OutputDir "manifest.json") -Encoding utf8

Export-SectionCsv (Join-Path $OutputDir "disk_info.csv") {
    Get-Disk -ErrorAction Stop |
        Select-Object Number, FriendlyName, SerialNumber, BusType, MediaType, Size, PartitionStyle, HealthStatus, OperationalStatus, IsBoot, IsSystem
}

Export-SectionCsv (Join-Path $OutputDir "physical_disk.csv") {
    Get-PhysicalDisk -ErrorAction Stop |
        Select-Object FriendlyName, SerialNumber, MediaType, BusType, CanPool, CannotPoolReason, HealthStatus, OperationalStatus, Size, SpindleSpeed, UniqueId
}

Export-SectionCsv (Join-Path $OutputDir "storage_reliability_counters.csv") {
    Get-PhysicalDisk -ErrorAction Stop |
        Get-StorageReliabilityCounter -ErrorAction Stop |
        Select-Object DeviceId, Temperature, TemperatureMax, ReadErrorsTotal, WriteErrorsTotal, ReadErrorsUncorrected, WriteErrorsUncorrected, Wear, PowerOnHours, StartStopCycleCount, LoadUnloadCycleCount
}

Export-SectionCsv (Join-Path $OutputDir "volume_info.csv") {
    Get-Volume -ErrorAction Stop |
        Select-Object DriveLetter, FileSystemLabel, FileSystem, DriveType, HealthStatus, OperationalStatus, Size, SizeRemaining
}

Export-SectionCsv (Join-Path $OutputDir "partition_info.csv") {
    Get-Partition -ErrorAction Stop |
        Select-Object DiskNumber, PartitionNumber, DriveLetter, Type, Size, Offset, IsBoot, IsSystem
}

Export-SectionCsv (Join-Path $OutputDir "logical_disk_info.csv") {
    Get-CimInstance Win32_LogicalDisk -ErrorAction Stop |
        Select-Object DeviceID, VolumeName, FileSystem, DriveType, Size, FreeSpace
}

Export-SectionCsv (Join-Path $OutputDir "win32_diskdrive.csv") {
    Get-CimInstance Win32_DiskDrive -ErrorAction Stop |
        Select-Object Index, Model, SerialNumber, InterfaceType, MediaType, Size, Partitions, Status, FirmwareRevision
}

Write-Section (Join-Path $OutputDir "fsutil_volume_diskfree_D.txt") {
    fsutil volume diskfree D:
}

Write-Section (Join-Path $OutputDir "driveinfo_D.txt") {
    $drive = New-Object System.IO.DriveInfo("D")
    [PSCustomObject]@{
        Name = $drive.Name
        DriveType = $drive.DriveType
        DriveFormat = $drive.DriveFormat
        IsReady = $drive.IsReady
        AvailableFreeGB = [math]::Round($drive.AvailableFreeSpace / 1GB, 2)
        TotalFreeGB = [math]::Round($drive.TotalFreeSpace / 1GB, 2)
        TotalGB = [math]::Round($drive.TotalSize / 1GB, 2)
    }
}

Write-Section (Join-Path $OutputDir "testfile_info.txt") {
    $testFile = Join-Path $BaseDir "fio_testfile_sustained_smoke"
    if (Test-Path $testFile) {
        Get-Item -LiteralPath $testFile | Select-Object FullName, Length, LastWriteTime
    }
    else {
        "Test file not found: $testFile"
    }
}

Write-Section (Join-Path $OutputDir "smartctl_availability.txt") {
    Get-Command smartctl -ErrorAction SilentlyContinue
}

if ($env:SSD_LAB_SMARTCTL_SCAN -eq "1") {
    Write-Native (Join-Path $OutputDir "smartctl_scan.txt") "smartctl" @("--scan-open")
}
else {
    "Not run by default. Set SSD_LAB_SMARTCTL_SCAN=1 to run smartctl --scan-open." |
        Out-File -FilePath (Join-Path $OutputDir "smartctl_scan.txt") -Encoding utf8
}

if (Test-Path $LatestDir) {
    Remove-Item -LiteralPath $LatestDir -Recurse -Force
}

Copy-Item -Path $OutputDir -Destination $LatestDir -Recurse -Force

Write-Host "=== Storage telemetry collected ==="
Write-Host "Output : $OutputDir"
Write-Host "Latest : $LatestDir"
