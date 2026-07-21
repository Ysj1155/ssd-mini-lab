# collect_storage_telemetry_windows.ps1
#
# Purpose:
#   Collect read-only storage telemetry for SSD mini-lab interpretation.
#
# Output:
#   results/telemetry/<timestamp>/
#
# Safety:
#   This script does not run fio or write to raw block devices.

param(
    [string]$TestFile = $env:SSD_LAB_EXTERNAL_TESTFILE
)

$ErrorActionPreference = "Continue"

$BaseDir = Split-Path -Parent $PSScriptRoot
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputRoot = Join-Path $BaseDir "results\telemetry"
$OutputDir = Join-Path $OutputRoot $Timestamp
$LatestDir = Join-Path $OutputRoot "latest"

if ([string]::IsNullOrWhiteSpace($TestFile)) {
    $TestFile = Join-Path $BaseDir "fio_testfile_sustained_smoke"
}

$TargetRoot = [System.IO.Path]::GetPathRoot($TestFile)
if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    throw "TestFile must be an absolute path: $TestFile"
}

$TargetDrive = $TargetRoot.TrimEnd('\').TrimEnd(':')
$Limitations = [System.Collections.Generic.List[string]]::new()

New-Item -ItemType Directory -Force $OutputDir | Out-Null

function Add-Limitation {
    param([string]$Message)
    [void]$script:Limitations.Add($Message)
}

function Write-Section {
    param(
        [string]$Path,
        [scriptblock]$Command
    )

    try {
        & $Command *>&1 | Out-File -FilePath $Path -Encoding utf8
    }
    catch {
        $message = $_.Exception.Message
        "ERROR: $message" | Out-File -FilePath $Path -Encoding utf8
        Add-Limitation "$([System.IO.Path]::GetFileName($Path)): $message"
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
        $message = $_.Exception.Message
        "ERROR: $message" | Out-File -FilePath $Path -Encoding utf8
        Add-Limitation "$([System.IO.Path]::GetFileName($Path)): $message"
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
        if ($LASTEXITCODE -ne 0) {
            Add-Limitation "$([System.IO.Path]::GetFileName($Path)): native command exit code $LASTEXITCODE"
        }
    }
    catch {
        $message = $_.Exception.Message
        "ERROR: $message" | Out-File -FilePath $Path -Encoding utf8
        Add-Limitation "$([System.IO.Path]::GetFileName($Path)): $message"
    }
}

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

Export-SectionCsv (Join-Path $OutputDir "target_volume_info.csv") {
    Get-Volume -DriveLetter $TargetDrive -ErrorAction Stop |
        Select-Object DriveLetter, FileSystemLabel, FileSystem, DriveType, HealthStatus, OperationalStatus, Size, SizeRemaining
}

Export-SectionCsv (Join-Path $OutputDir "target_disk_info.csv") {
    Get-Partition -DriveLetter $TargetDrive -ErrorAction Stop |
        Get-Disk -ErrorAction Stop |
        Select-Object Number, FriendlyName, SerialNumber, BusType, MediaType, Size, PartitionStyle, HealthStatus, OperationalStatus
}

Write-Section (Join-Path $OutputDir "target_volume_diskfree.txt") {
    fsutil volume diskfree "${TargetDrive}:"
    if ($LASTEXITCODE -ne 0) {
        throw "fsutil exit code $LASTEXITCODE"
    }
}

Write-Section (Join-Path $OutputDir "target_driveinfo.txt") {
    $drive = New-Object System.IO.DriveInfo($TargetDrive)
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
    if (-not (Test-Path -LiteralPath $TestFile)) {
        throw "Test file not found: $TestFile"
    }
    Get-Item -LiteralPath $TestFile | Select-Object FullName, Length, LastWriteTime
}

$Smartctl = Get-Command smartctl -ErrorAction SilentlyContinue
if ($null -eq $Smartctl) {
    "smartctl command not available" | Out-File -FilePath (Join-Path $OutputDir "smartctl_availability.txt") -Encoding utf8
    Add-Limitation "smartctl command not available"
}
else {
    $Smartctl | Out-File -FilePath (Join-Path $OutputDir "smartctl_availability.txt") -Encoding utf8
}

if ($env:SSD_LAB_SMARTCTL_SCAN -eq "1" -and $null -ne $Smartctl) {
    Write-Native (Join-Path $OutputDir "smartctl_scan.txt") "smartctl" @("--scan-open")
}
else {
    "Not run. Set SSD_LAB_SMARTCTL_SCAN=1 and install smartctl to enable scan-open." |
        Out-File -FilePath (Join-Path $OutputDir "smartctl_scan.txt") -Encoding utf8
    Add-Limitation "smartctl scan not available or not requested"
}

$Status = if ($Limitations.Count -eq 0) { "complete" } else { "limited" }
$Manifest = [ordered]@{
    schema_version = "1.0"
    collected_at = (Get-Date).ToString("o")
    base_dir = $BaseDir
    output_dir = $OutputDir
    collector = "scripts/collect_storage_telemetry_windows.ps1"
    status = $Status
    target_file = $TestFile
    target_drive = $TargetDrive
    limitations = @($Limitations)
    safety = "read-only metadata and telemetry queries; no fio; no raw-device writes"
}

$Manifest |
    ConvertTo-Json -Depth 5 |
    Out-File -FilePath (Join-Path $OutputDir "manifest.json") -Encoding utf8

if (Test-Path $LatestDir) {
    Remove-Item -LiteralPath $LatestDir -Recurse -Force
}

Copy-Item -Path $OutputDir -Destination $LatestDir -Recurse -Force

Write-Host "=== Storage telemetry collected ==="
Write-Host "Status : $Status"
Write-Host "Target : $TestFile"
Write-Host "Drive  : $TargetDrive"
Write-Host "Output : $OutputDir"
Write-Host "Latest : $LatestDir"
