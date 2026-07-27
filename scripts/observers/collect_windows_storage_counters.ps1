# scripts/observers/collect_windows_storage_counters.ps1
#
# Collect host-visible Windows logical-disk counters on the same time axis as
# one fio phase. This observer is read-only and exits successfully with a
# "limited" manifest when the requested counters are unavailable.

param(
    [Parameter(Mandatory = $true)]
    [string]$RunId,

    [Parameter(Mandatory = $true)]
    [string]$Phase,

    [ValidatePattern('^[A-Za-z]$')]
    [string]$TargetDrive = "E",

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [Parameter(Mandatory = $true)]
    [string]$StopFile,

    [ValidateRange(100, 60000)]
    [int]$SampleIntervalMs = 1000,

    [ValidateRange(1, 86400)]
    [int]$MaxDurationSec = 900
)

$ErrorActionPreference = "Stop"

$SafePhase = $Phase -replace '[^A-Za-z0-9_.-]', '_'
$DriveInstance = "$($TargetDrive.ToUpper()):"
$CsvPath = Join-Path $OutputDir "${SafePhase}_windows_storage_counters.csv"
$ManifestPath = Join-Path $OutputDir "${SafePhase}_manifest.json"
$StartedAt = (Get-Date).ToString("o")
$Samples = [System.Collections.Generic.List[object]]::new()
$Errors = [System.Collections.Generic.List[string]]::new()
$StopReason = "max_duration"

New-Item -ItemType Directory -Force $OutputDir | Out-Null

try {
    $Volume = Get-Volume -DriveLetter $TargetDrive -ErrorAction Stop
    $VolumeIdentity = [ordered]@{
        drive_letter = $TargetDrive.ToUpper()
        friendly_name = $Volume.FriendlyName
        file_system_type = [string]$Volume.FileSystemType
        health_status = [string]$Volume.HealthStatus
        operational_status = @($Volume.OperationalStatus | ForEach-Object { [string]$_ })
        size_bytes = [long]$Volume.Size
        size_remaining_bytes = [long]$Volume.SizeRemaining
    }
}
catch {
    $VolumeIdentity = [ordered]@{
        drive_letter = $TargetDrive.ToUpper()
        collection_error = $_.Exception.Message
    }
    $Errors.Add("volume_identity: $($_.Exception.Message)")
}

$Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
while ($Stopwatch.Elapsed.TotalSeconds -lt $MaxDurationSec) {
    if (Test-Path -LiteralPath $StopFile) {
        $StopReason = "stop_file"
        break
    }

    $SampledAt = Get-Date
    try {
        $Counter = Get-CimInstance `
            -ClassName Win32_PerfFormattedData_PerfDisk_LogicalDisk `
            -Filter "Name='$DriveInstance'" `
            -ErrorAction Stop

        if ($null -eq $Counter) {
            throw "Logical-disk counter instance '$DriveInstance' was not found."
        }

        $Samples.Add([pscustomobject][ordered]@{
            sampled_at = $SampledAt.ToString("o")
            elapsed_ms = [math]::Round($Stopwatch.Elapsed.TotalMilliseconds, 3)
            drive_instance = $DriveInstance
            disk_bytes_per_sec = [long]$Counter.DiskBytesPersec
            disk_read_bytes_per_sec = [long]$Counter.DiskReadBytesPersec
            disk_write_bytes_per_sec = [long]$Counter.DiskWriteBytesPersec
            disk_reads_per_sec = [long]$Counter.DiskReadsPersec
            disk_writes_per_sec = [long]$Counter.DiskWritesPersec
            avg_disk_sec_per_read = [double]$Counter.AvgDisksecPerRead
            avg_disk_sec_per_write = [double]$Counter.AvgDisksecPerWrite
            current_disk_queue_length = [long]$Counter.CurrentDiskQueueLength
            percent_disk_time = [double]$Counter.PercentDiskTime
        })
    }
    catch {
        $Errors.Add("$($SampledAt.ToString('o')): $($_.Exception.Message)")
    }

    Start-Sleep -Milliseconds $SampleIntervalMs
}
$Stopwatch.Stop()

if ($Samples.Count -gt 0) {
    $Samples | Export-Csv -LiteralPath $CsvPath -NoTypeInformation -Encoding utf8
}

$UniqueErrors = @($Errors | Select-Object -Unique)
$ActiveSampleCount = @(
    $Samples | Where-Object {
        $_.disk_bytes_per_sec -gt 0 -or
        $_.disk_read_bytes_per_sec -gt 0 -or
        $_.disk_write_bytes_per_sec -gt 0
    }
).Count
$Status = if (
    $Samples.Count -gt 0 -and
    $ActiveSampleCount -gt 0 -and
    $UniqueErrors.Count -eq 0
) { "complete" } else { "limited" }
$Manifest = [ordered]@{
    schema_version = "1.0"
    role = "host_observer"
    run_id = $RunId
    phase = $Phase
    started_at = $StartedAt
    completed_at = (Get-Date).ToString("o")
    status = $Status
    observer = "scripts/observers/collect_windows_storage_counters.ps1"
    safety = "read-only Windows logical-disk counter collection; no fio execution and no storage writes"
    target = $VolumeIdentity
    sampling = [ordered]@{
        requested_interval_ms = $SampleIntervalMs
        maximum_duration_sec = $MaxDurationSec
        observed_duration_sec = [math]::Round($Stopwatch.Elapsed.TotalSeconds, 3)
        sample_count = $Samples.Count
        active_sample_count = $ActiveSampleCount
        stop_reason = $StopReason
    }
    artifacts = [ordered]@{
        counter_csv = if ($Samples.Count -gt 0) { $CsvPath } else { $null }
        stop_file = $StopFile
    }
    limitations = @(
        "Host-visible logical-disk counters do not identify SSD firmware, NAND, FTL, or USB bridge root causes."
        if ($ActiveSampleCount -eq 0) {
            "No nonzero disk activity was observed while the fio phase was active; synchronized host evidence is not usable."
        }
        if ($UniqueErrors.Count -gt 0) {
            "One or more counter samples could not be collected; see errors."
        }
    )
    errors = $UniqueErrors
}

$Manifest | ConvertTo-Json -Depth 8 |
    Out-File -LiteralPath $ManifestPath -Encoding utf8

Write-Host "=== Windows storage counter observer completed ==="
Write-Host "Run ID   : $RunId"
Write-Host "Phase    : $Phase"
Write-Host "Status   : $Status"
Write-Host "Samples  : $($Samples.Count)"
Write-Host "Manifest : $ManifestPath"

exit 0
