# collect_env_windows.ps1
#
# Purpose:
#   Collect a read-only environment snapshot for SSD mini-lab experiments.
#
# Output:
#   results/env/<timestamp>/
#
# Notes:
#   This script does not run fio and does not write to any disk device.
#   It only records host, tool, disk, volume, Git, Python, and WSL state.

$ErrorActionPreference = "Continue"

$BaseDir = Split-Path -Parent $PSScriptRoot
$SafeGitDir = $BaseDir.Replace("\", "/")
$WslDistro = $env:SSD_LAB_WSL_DISTRO
if ([string]::IsNullOrWhiteSpace($WslDistro)) {
    $WslDistro = "Ubuntu"
}
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputRoot = Join-Path $BaseDir "results\env"
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
    collector = "scripts/collect_env_windows.ps1"
    wsl_distro = $WslDistro
}

$manifest | ConvertTo-Json -Depth 3 | Out-File -FilePath (Join-Path $OutputDir "manifest.json") -Encoding utf8

Write-Section (Join-Path $OutputDir "powershell_version.txt") {
    $PSVersionTable
}

Write-Section (Join-Path $OutputDir "windows_computer_info.txt") {
    Get-ComputerInfo | Select-Object `
        WindowsProductName,
        WindowsVersion,
        OsBuildNumber,
        OsArchitecture,
        CsManufacturer,
        CsModel,
        CsProcessors,
        CsTotalPhysicalMemory
}

Write-Section (Join-Path $OutputDir "cpu_memory.txt") {
    Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed
    ""
    Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, TotalPhysicalMemory
}

try {
    Get-Disk -ErrorAction Stop |
        Select-Object Number, FriendlyName, SerialNumber, BusType, MediaType, Size, PartitionStyle, HealthStatus, OperationalStatus |
        Export-Csv -Path (Join-Path $OutputDir "disk_info.csv") -NoTypeInformation -Encoding utf8
}
catch {
    "ERROR: $($_.Exception.Message)" | Out-File -FilePath (Join-Path $OutputDir "disk_info.csv") -Encoding utf8
}

try {
    Get-Volume -ErrorAction Stop |
        Select-Object DriveLetter, FileSystemLabel, FileSystem, DriveType, HealthStatus, Size, SizeRemaining |
        Export-Csv -Path (Join-Path $OutputDir "volume_info.csv") -NoTypeInformation -Encoding utf8
}
catch {
    "ERROR: $($_.Exception.Message)" | Out-File -FilePath (Join-Path $OutputDir "volume_info.csv") -Encoding utf8
}

try {
    Get-CimInstance Win32_LogicalDisk -ErrorAction Stop |
        Select-Object DeviceID, VolumeName, FileSystem, DriveType, Size, FreeSpace |
        Export-Csv -Path (Join-Path $OutputDir "logical_disk_info.csv") -NoTypeInformation -Encoding utf8
}
catch {
    "ERROR: $($_.Exception.Message)" | Out-File -FilePath (Join-Path $OutputDir "logical_disk_info.csv") -Encoding utf8
}

try {
    Get-PSDrive -PSProvider FileSystem |
        Select-Object Name, Root, Used, Free, Description |
        Export-Csv -Path (Join-Path $OutputDir "psdrive_filesystem_info.csv") -NoTypeInformation -Encoding utf8
}
catch {
    "ERROR: $($_.Exception.Message)" | Out-File -FilePath (Join-Path $OutputDir "psdrive_filesystem_info.csv") -Encoding utf8
}

Write-Native (Join-Path $OutputDir "fio_version.txt") "fio" @("--version")
Write-Native (Join-Path $OutputDir "python_version.txt") "python" @("--version")
Write-Native (Join-Path $OutputDir "pip_freeze.txt") "python" @("-m", "pip", "freeze")
Write-Native (Join-Path $OutputDir "git_version.txt") "git" @("--version")

Write-Section (Join-Path $OutputDir "git_state.txt") {
    git -c safe.directory=$SafeGitDir -C $BaseDir rev-parse --show-toplevel
    git -c safe.directory=$SafeGitDir -C $BaseDir rev-parse HEAD
    git -c safe.directory=$SafeGitDir -C $BaseDir status --short --branch
}

Write-Native (Join-Path $OutputDir "wsl_status.txt") "wsl.exe" @("--status")
Write-Native (Join-Path $OutputDir "wsl_list.txt") "wsl.exe" @("-l", "-v")

Write-Native (Join-Path $OutputDir "wsl_linux_env.txt") "wsl.exe" @(
    "-d",
    $WslDistro,
    "--",
    "sh",
    "-lc",
    "uname -a; echo; cat /etc/os-release 2>/dev/null; echo; lsblk 2>/dev/null; echo; df -h 2>/dev/null"
)

Write-Native (Join-Path $OutputDir "wsl_tool_versions.txt") "wsl.exe" @(
    "-d",
    $WslDistro,
    "--",
    "sh",
    "-lc",
    "command -v fio && fio --version; echo; command -v python3 && python3 --version; echo; command -v git && git --version; echo; command -v iostat && iostat -V"
)

if (Test-Path $LatestDir) {
    Remove-Item -LiteralPath $LatestDir -Recurse -Force
}

Copy-Item -Path $OutputDir -Destination $LatestDir -Recurse -Force

Write-Host "=== Environment snapshot collected ==="
Write-Host "Output : $OutputDir"
Write-Host "Latest : $LatestDir"
